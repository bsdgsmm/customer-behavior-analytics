import numpy as np
import pandas as pd
import pytest

from src.retention_analysis import (
    average_retention_curve,
    cohort_counts,
    cohort_cumulative_revenue_per_customer,
    cohort_retention,
    customer_lifetime_revenue,
    customer_type_breakdown,
    days_to_second_order,
    lifetime_revenue_statistics,
    monthly_customer_activity,
    months_between,
    repeat_purchase_summary,
)

DECEMBER = pd.Timestamp("2010-12-01")
FEBRUARY = pd.Timestamp("2011-02-01")


@pytest.fixture
def transactions(cleaning_result):
    return cleaning_result.transactions


def test_months_between():
    start = pd.Series(pd.to_datetime(["2010-12-01", "2011-01-01"]))
    end = pd.Series(pd.to_datetime(["2011-02-01", "2011-01-01"]))
    assert list(months_between(start, end)) == [2, 0]


def test_repeat_purchase_summary(transactions):
    summary = repeat_purchase_summary(transactions)
    assert summary["customers"] == 3
    assert summary["repeat_customers"] == 1
    assert summary["repeat_purchase_rate"] == pytest.approx(1 / 3)
    assert summary["repeat_customer_revenue_share"] == pytest.approx(135.0 / 176.14)
    assert summary["repeat_customer_order_share"] == pytest.approx(2 / 4)


def test_customer_type_breakdown(transactions):
    breakdown = customer_type_breakdown(transactions).set_index("customer_type")
    assert breakdown.loc["One-time", "customers"] == 2
    assert breakdown.loc["Returning", "revenue"] == pytest.approx(135.0)
    assert breakdown["customer_share"].sum() == pytest.approx(1.0)


def test_days_to_second_order(transactions):
    days = days_to_second_order(transactions)
    assert days.to_dict() == {"12583": 45}


def test_monthly_customer_activity(transactions):
    activity = monthly_customer_activity(transactions).set_index("month")
    assert activity.loc[DECEMBER, "new_customers"] == 2
    assert activity.loc[pd.Timestamp("2011-01-01"), "returning_customers"] == 1
    assert activity.loc[FEBRUARY, "new_customers"] == 1
    assert (activity["new_customers"] + activity["returning_customers"] == activity["active_customers"]).all()
    assert activity["cumulative_customers"].iloc[-1] == 3


def test_cohort_counts_and_retention(transactions):
    counts = cohort_counts(transactions)
    assert counts.loc[DECEMBER].tolist() == [2, 1, 0]
    assert counts.loc[FEBRUARY, 0] == 1
    assert np.isnan(counts.loc[FEBRUARY, 1])
    retention = cohort_retention(transactions)
    assert retention.loc[DECEMBER].tolist() == [1.0, 0.5, 0.0]


def test_average_retention_curve_weights_by_eligible_customers(transactions):
    curve = average_retention_curve(transactions).set_index("months_since_acquisition")
    assert curve.loc[0, "retention_rate"] == pytest.approx(1.0)
    assert curve.loc[1, "eligible_customers"] == 2
    assert curve.loc[1, "retention_rate"] == pytest.approx(0.5)
    assert curve.loc[2, "retention_rate"] == pytest.approx(0.0)


def test_cohort_cumulative_revenue(transactions):
    revenue = cohort_cumulative_revenue_per_customer(transactions)
    assert revenue.loc[DECEMBER].tolist() == pytest.approx([62.82, 85.32, 85.32])
    assert revenue.loc[FEBRUARY, 0] == pytest.approx(5.5)


def test_customer_lifetime_revenue(transactions):
    lifetime = customer_lifetime_revenue(transactions).set_index("customer_id")
    assert lifetime.loc["12583", "lifetime_revenue"] == pytest.approx(135.0)
    assert lifetime["lifetime_revenue"].sum() == pytest.approx(transactions["revenue"].sum())
    statistics = lifetime_revenue_statistics(transactions)
    assert statistics["max"] == pytest.approx(135.0)
    assert statistics["median"] == pytest.approx(35.64)
