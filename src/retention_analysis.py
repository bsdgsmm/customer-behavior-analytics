import pandas as pd

from src.aggregations import build_customer_summary, build_orders


def months_between(start: pd.Series, end: pd.Series) -> pd.Series:
    return (end.dt.year - start.dt.year) * 12 + (end.dt.month - start.dt.month)


def repeat_purchase_summary(transactions: pd.DataFrame) -> dict:
    customers = build_customer_summary(transactions)
    repeat = customers[customers["is_repeat_customer"]]
    total_revenue = customers["revenue"].sum()
    total_orders = customers["orders"].sum()
    return {
        "customers": len(customers),
        "repeat_customers": len(repeat),
        "one_time_customers": int(len(customers) - len(repeat)),
        "repeat_purchase_rate": float(len(repeat) / len(customers)) if len(customers) else 0.0,
        "repeat_customer_revenue": float(repeat["revenue"].sum()),
        "repeat_customer_revenue_share": float(repeat["revenue"].sum() / total_revenue) if total_revenue else 0.0,
        "repeat_customer_order_share": float(repeat["orders"].sum() / total_orders) if total_orders else 0.0,
    }


def customer_type_breakdown(transactions: pd.DataFrame) -> pd.DataFrame:
    customers = build_customer_summary(transactions)
    customers["customer_type"] = customers["is_repeat_customer"].map({True: "Returning", False: "One-time"})
    table = (
        customers.groupby("customer_type")
        .agg(
            customers=("customer_id", "nunique"),
            orders=("orders", "sum"),
            revenue=("revenue", "sum"),
            mean_revenue_per_customer=("revenue", "mean"),
            median_revenue_per_customer=("revenue", "median"),
        )
        .reindex(["One-time", "Returning"])
        .fillna(0)
        .reset_index()
    )
    table["customer_share"] = table["customers"] / table["customers"].sum()
    table["revenue_share"] = table["revenue"] / table["revenue"].sum()
    return table


def days_to_second_order(transactions: pd.DataFrame) -> pd.Series:
    orders = build_orders(transactions).sort_values(["customer_id", "order_date"])
    orders["order_number"] = orders.groupby("customer_id").cumcount() + 1
    first = orders[orders["order_number"] == 1].set_index("customer_id")["order_date"]
    second = orders[orders["order_number"] == 2].set_index("customer_id")["order_date"]
    return (second - first.reindex(second.index)).dt.days.rename("days_to_second_order")


def monthly_customer_activity(transactions: pd.DataFrame) -> pd.DataFrame:
    orders = build_orders(transactions)
    acquisition = orders.groupby("customer_id")["order_month"].min().rename("acquisition_month")
    orders = orders.join(acquisition, on="customer_id")
    orders["customer_status"] = (orders["order_month"] == orders["acquisition_month"]).map(
        {True: "new", False: "returning"}
    )
    active = orders.groupby(["order_month", "customer_status"])["customer_id"].nunique().unstack(fill_value=0)
    revenue = orders.groupby(["order_month", "customer_status"])["revenue"].sum().unstack(fill_value=0.0)
    table = pd.DataFrame(
        {
            "active_customers": orders.groupby("order_month")["customer_id"].nunique(),
            "new_customers": active.get("new", 0),
            "returning_customers": active.get("returning", 0),
            "new_customer_revenue": revenue.get("new", 0.0),
            "returning_customer_revenue": revenue.get("returning", 0.0),
        }
    ).fillna(0)
    table["returning_customer_share"] = table["returning_customers"] / table["active_customers"]
    table["returning_revenue_share"] = table["returning_customer_revenue"] / (
        table["new_customer_revenue"] + table["returning_customer_revenue"]
    )
    table["cumulative_customers"] = table["new_customers"].cumsum()
    return table.rename_axis("month").reset_index()


def cohort_activity(transactions: pd.DataFrame) -> pd.DataFrame:
    orders = build_orders(transactions)
    acquisition = orders.groupby("customer_id")["order_month"].min().rename("cohort_month")
    orders = orders.join(acquisition, on="customer_id")
    orders["months_since_acquisition"] = months_between(orders["cohort_month"], orders["order_month"])
    return orders


def observable_periods(cohort_table: pd.DataFrame, last_month: pd.Timestamp) -> pd.DataFrame:
    cohorts = pd.Series(cohort_table.index, index=cohort_table.index)
    horizon = months_between(cohorts, pd.Series(last_month, index=cohort_table.index))
    return pd.DataFrame({period: horizon >= period for period in cohort_table.columns}, index=cohort_table.index)


def _cohort_pivot(transactions: pd.DataFrame, values: str, aggfunc: str) -> pd.DataFrame:
    orders = cohort_activity(transactions)
    table = orders.pivot_table(
        index="cohort_month", columns="months_since_acquisition", values=values, aggfunc=aggfunc, fill_value=0
    )
    last_month = orders["order_month"].max()
    first_cohort = orders["cohort_month"].min()
    horizon = (last_month.year - first_cohort.year) * 12 + last_month.month - first_cohort.month
    table = table.reindex(columns=range(horizon + 1), fill_value=0)
    return table.where(observable_periods(table, last_month))


def cohort_counts(transactions: pd.DataFrame) -> pd.DataFrame:
    return _cohort_pivot(transactions, "customer_id", "nunique")


def cohort_retention(transactions: pd.DataFrame) -> pd.DataFrame:
    counts = cohort_counts(transactions)
    return counts.divide(counts[0], axis=0)


def average_retention_curve(transactions: pd.DataFrame) -> pd.DataFrame:
    counts = cohort_counts(transactions)
    retained = counts.sum(axis=0)
    eligible = counts.notna().mul(counts[0], axis=0).sum(axis=0)
    curve = pd.DataFrame(
        {"retained_customers": retained, "eligible_customers": eligible, "cohorts": counts.notna().sum(axis=0)}
    )
    curve["retention_rate"] = curve["retained_customers"] / curve["eligible_customers"]
    return curve.rename_axis("months_since_acquisition").reset_index()


def cohort_cumulative_revenue_per_customer(transactions: pd.DataFrame) -> pd.DataFrame:
    revenue = _cohort_pivot(transactions, "revenue", "sum")
    cohort_size = cohort_counts(transactions)[0]
    return revenue.cumsum(axis=1).where(revenue.notna()).divide(cohort_size, axis=0)


def customer_lifetime_revenue(transactions: pd.DataFrame) -> pd.DataFrame:
    customers = build_customer_summary(transactions)
    customers["observed_days"] = (transactions["order_date"].max() - customers["first_order_date"]).dt.days
    return customers[
        [
            "customer_id",
            "acquisition_month",
            "first_order_date",
            "last_order_date",
            "observed_days",
            "orders",
            "revenue",
        ]
    ].rename(columns={"revenue": "lifetime_revenue"})


def lifetime_revenue_statistics(transactions: pd.DataFrame) -> dict:
    lifetime = customer_lifetime_revenue(transactions)["lifetime_revenue"]
    return {
        "mean": float(lifetime.mean()),
        "median": float(lifetime.median()),
        "p75": float(lifetime.quantile(0.75)),
        "p90": float(lifetime.quantile(0.90)),
        "p99": float(lifetime.quantile(0.99)),
        "max": float(lifetime.max()),
    }
