import pandas as pd


def build_orders(transactions: pd.DataFrame) -> pd.DataFrame:
    orders = (
        transactions.groupby("order_id", as_index=False)
        .agg(
            customer_id=("customer_id", "first"),
            order_date=("order_date", "min"),
            country=("country", "first"),
            line_items=("product_id", "size"),
            units=("quantity", "sum"),
            revenue=("revenue", "sum"),
        )
        .sort_values(["order_date", "order_id"])
        .reset_index(drop=True)
    )
    orders["order_month"] = orders["order_date"].dt.to_period("M").dt.to_timestamp()
    orders["order_quarter"] = orders["order_date"].dt.to_period("Q").astype(str)
    return orders


def build_customer_summary(transactions: pd.DataFrame) -> pd.DataFrame:
    orders = build_orders(transactions)
    customers = (
        orders.groupby("customer_id", as_index=False)
        .agg(
            first_order_date=("order_date", "min"),
            last_order_date=("order_date", "max"),
            orders=("order_id", "nunique"),
            units=("units", "sum"),
            revenue=("revenue", "sum"),
            country=("country", "first"),
        )
        .sort_values("customer_id")
        .reset_index(drop=True)
    )
    customers["average_order_value"] = customers["revenue"] / customers["orders"]
    customers["is_repeat_customer"] = customers["orders"] >= 2
    customers["acquisition_month"] = customers["first_order_date"].dt.to_period("M").dt.to_timestamp()
    return customers
