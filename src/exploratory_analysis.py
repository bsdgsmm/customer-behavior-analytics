import pandas as pd

from src.aggregations import build_orders


def summary_kpis(transactions: pd.DataFrame) -> dict:
    orders = build_orders(transactions)
    total_revenue = float(transactions["revenue"].sum())
    total_orders = int(orders["order_id"].nunique())
    return {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "unique_customers": int(transactions["customer_id"].nunique()),
        "unique_products": int(transactions["product_id"].nunique()),
        "countries": int(transactions["country"].nunique()),
        "total_units_sold": int(transactions["quantity"].sum()),
        "average_order_value": round(total_revenue / total_orders, 2) if total_orders else 0.0,
        "average_units_per_order": round(float(orders["units"].mean()), 2) if total_orders else 0.0,
        "first_order_date": transactions["order_date"].min().strftime("%Y-%m-%d"),
        "last_order_date": transactions["order_date"].max().strftime("%Y-%m-%d"),
    }


def product_performance(transactions: pd.DataFrame) -> pd.DataFrame:
    products = (
        transactions.groupby(["product_id", "product_name"], as_index=False)
        .agg(
            units_sold=("quantity", "sum"),
            revenue=("revenue", "sum"),
            orders=("order_id", "nunique"),
            customers=("customer_id", "nunique"),
        )
        .sort_values(["revenue", "product_id"], ascending=[False, True])
        .reset_index(drop=True)
    )
    products["revenue_share"] = products["revenue"] / products["revenue"].sum()
    products["cumulative_revenue_share"] = products["revenue_share"].cumsum()
    products["order_penetration"] = products["orders"] / transactions["order_id"].nunique()
    return products


def top_products(transactions: pd.DataFrame, by: str = "revenue", n: int = 10) -> pd.DataFrame:
    if by not in {"revenue", "units_sold", "orders", "customers"}:
        raise ValueError(f"Unsupported ranking column: {by}")
    return product_performance(transactions).nlargest(n, by).reset_index(drop=True)


def order_frequency_distribution(transactions: pd.DataFrame, cap: int = 10) -> pd.DataFrame:
    orders_per_customer = transactions.groupby("customer_id")["order_id"].nunique()
    labels = [str(value) for value in range(1, cap)] + [f"{cap}+"]
    buckets = orders_per_customer.clip(upper=cap).map(lambda value: labels[value - 1])
    distribution = buckets.value_counts().reindex(labels, fill_value=0)
    frame = pd.DataFrame({"orders_per_customer": labels, "customers": distribution.to_numpy()})
    frame["share_of_customers"] = frame["customers"] / frame["customers"].sum()
    return frame


def sales_by_weekday_and_hour(transactions: pd.DataFrame) -> pd.DataFrame:
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    table = transactions.pivot_table(
        index="order_day_of_week", columns="order_hour", values="revenue", aggfunc="sum", fill_value=0.0
    )
    return table.reindex([day for day in weekdays if day in table.index])
