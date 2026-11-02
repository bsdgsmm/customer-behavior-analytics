import pandas as pd

from src.aggregations import build_customer_summary, build_orders

PERIOD_COLUMNS = {"month": "order_month", "quarter": "order_quarter"}


def revenue_by_period(transactions: pd.DataFrame, period: str = "month") -> pd.DataFrame:
    column = PERIOD_COLUMNS.get(period)
    if column is None:
        raise ValueError("period must be 'month' or 'quarter'")
    orders = build_orders(transactions)
    table = (
        orders.groupby(column, as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            orders=("order_id", "nunique"),
            customers=("customer_id", "nunique"),
            units=("units", "sum"),
        )
        .rename(columns={column: period})
        .sort_values(period)
        .reset_index(drop=True)
    )
    table["average_order_value"] = table["revenue"] / table["orders"]
    table["revenue_per_customer"] = table["revenue"] / table["customers"]
    table["revenue_change_pct"] = table["revenue"].pct_change()
    return table


def month_coverage(transactions: pd.DataFrame) -> pd.DataFrame:
    coverage = (
        transactions.assign(order_day=transactions["order_date"].dt.normalize())
        .groupby("order_month")
        .agg(first_day=("order_day", "min"), last_day=("order_day", "max"), trading_days=("order_day", "nunique"))
        .reset_index()
        .rename(columns={"order_month": "month"})
    )
    data_start = transactions["order_date"].min().normalize()
    data_end = transactions["order_date"].max().normalize()
    month_end = coverage["month"] + pd.offsets.MonthEnd(0)
    starts_late = (coverage["month"] < data_start) & (coverage["first_day"] == data_start)
    ends_early = (month_end > data_end) & (coverage["last_day"] == data_end)
    coverage["is_partial_month"] = starts_late | ends_early
    return coverage


def complete_months(transactions: pd.DataFrame) -> pd.Series:
    coverage = month_coverage(transactions)
    return coverage.loc[~coverage["is_partial_month"], "month"]


def revenue_concentration(
    transactions: pd.DataFrame, shares: tuple[float, ...] = (0.01, 0.05, 0.10, 0.20, 0.50)
) -> pd.DataFrame:
    revenue = build_customer_summary(transactions)["revenue"].sort_values(ascending=False)
    total = revenue.sum()
    rows = []
    for share in shares:
        top_n = max(1, int(round(len(revenue) * share)))
        top_revenue = revenue.head(top_n).sum()
        rows.append(
            {
                "top_customer_share": share,
                "customers": top_n,
                "revenue": top_revenue,
                "revenue_share": top_revenue / total,
            }
        )
    return pd.DataFrame(rows)


def pareto_curve(transactions: pd.DataFrame) -> pd.DataFrame:
    revenue = build_customer_summary(transactions)["revenue"].sort_values(ascending=False).reset_index(drop=True)
    return pd.DataFrame(
        {
            "customer_share": (revenue.index + 1) / len(revenue),
            "cumulative_revenue_share": revenue.cumsum() / revenue.sum(),
        }
    )


def top_customers(transactions: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    customers = build_customer_summary(transactions)
    customers["revenue_share"] = customers["revenue"] / customers["revenue"].sum()
    columns = [
        "customer_id",
        "country",
        "orders",
        "revenue",
        "revenue_share",
        "average_order_value",
        "first_order_date",
        "last_order_date",
    ]
    return customers.nlargest(n, "revenue")[columns].reset_index(drop=True)


def country_performance(transactions: pd.DataFrame) -> pd.DataFrame:
    orders = build_orders(transactions)
    table = (
        orders.groupby("country", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            orders=("order_id", "nunique"),
            customers=("customer_id", "nunique"),
            units=("units", "sum"),
        )
        .sort_values("revenue", ascending=False)
        .reset_index(drop=True)
    )
    table["revenue_share"] = table["revenue"] / table["revenue"].sum()
    table["average_order_value"] = table["revenue"] / table["orders"]
    table["revenue_per_customer"] = table["revenue"] / table["customers"]
    return table
