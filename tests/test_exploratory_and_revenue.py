import pandas as pd
import pytest

from src.aggregations import build_customer_summary, build_orders
from src.exploratory_analysis import order_frequency_distribution, summary_kpis, top_products
from src.revenue_analysis import (
    country_performance,
    month_coverage,
    pareto_curve,
    revenue_by_period,
    revenue_concentration,
    top_customers,
)


@pytest.fixture
def transactions(cleaning_result):
    return cleaning_result.transactions


def test_build_orders_aggregates_lines(transactions):
    orders = build_orders(transactions).set_index("order_id")
    assert orders.loc["536365", "line_items"] == 2
    assert orders.loc["536365", "revenue"] == pytest.approx(35.64)
    assert orders["revenue"].sum() == pytest.approx(transactions["revenue"].sum())


def test_customer_summary(transactions):
    customers = build_customer_summary(transactions).set_index("customer_id")
    assert customers.loc["12583", "orders"] == 2
    assert bool(customers.loc["12583", "is_repeat_customer"])
    assert not bool(customers.loc["17850", "is_repeat_customer"])
    assert customers.loc["12583", "acquisition_month"] == pd.Timestamp("2010-12-01")


def test_summary_kpis(transactions):
    kpis = summary_kpis(transactions)
    assert kpis["total_orders"] == 4
    assert kpis["unique_customers"] == 3
    assert kpis["total_units_sold"] == 58
    assert kpis["average_order_value"] == pytest.approx(round(kpis["total_revenue"] / 4, 2))


def test_top_products_ranking(transactions):
    ranked = top_products(transactions, by="revenue", n=2)
    assert ranked.loc[0, "product_id"] == "22728"
    assert ranked.loc[0, "revenue"] == pytest.approx(135.0)
    with pytest.raises(ValueError):
        top_products(transactions, by="margin")


def test_order_frequency_distribution(transactions):
    distribution = order_frequency_distribution(transactions, cap=3).set_index("orders_per_customer")
    assert distribution.loc["1", "customers"] == 2
    assert distribution.loc["2", "customers"] == 1
    assert distribution["share_of_customers"].sum() == pytest.approx(1.0)


def test_revenue_by_period(transactions):
    monthly = revenue_by_period(transactions, "month")
    quarterly = revenue_by_period(transactions, "quarter")
    assert monthly["revenue"].sum() == pytest.approx(transactions["revenue"].sum())
    assert quarterly["revenue"].sum() == pytest.approx(transactions["revenue"].sum())
    assert list(quarterly["quarter"]) == ["2010Q4", "2011Q1"]
    with pytest.raises(ValueError):
        revenue_by_period(transactions, "week")


def test_month_coverage_flags_only_truncated_edges():
    frame = pd.DataFrame(
        {"order_date": pd.to_datetime(["2011-01-01", "2011-01-31", "2011-02-01", "2011-02-28", "2011-03-01", "2011-03-09"])}
    )
    frame["order_month"] = frame["order_date"].dt.to_period("M").dt.to_timestamp()
    coverage = month_coverage(frame)
    assert list(coverage["is_partial_month"]) == [False, False, True]


def test_revenue_concentration_and_pareto(transactions):
    concentration = revenue_concentration(transactions, shares=(0.34, 1.0))
    assert concentration.loc[1, "revenue_share"] == pytest.approx(1.0)
    curve = pareto_curve(transactions)
    assert curve["cumulative_revenue_share"].is_monotonic_increasing
    assert curve["cumulative_revenue_share"].iloc[-1] == pytest.approx(1.0)


def test_top_customers_and_countries(transactions):
    customers = top_customers(transactions, n=1)
    assert customers.loc[0, "customer_id"] == "12583"
    countries = country_performance(transactions).set_index("country")
    assert countries.loc["France", "revenue"] == pytest.approx(135.0)
    assert countries["revenue_share"].sum() == pytest.approx(1.0)
