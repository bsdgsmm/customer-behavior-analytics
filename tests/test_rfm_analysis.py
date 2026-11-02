import pandas as pd
import pytest

from src.rfm_analysis import (
    DEFAULT_SEGMENT_RULES,
    RFMConfig,
    SegmentRule,
    assign_segments,
    calculate_rfm,
    percentile_score,
    score_thresholds,
    segment_activity_change,
    segment_summary,
)


def make_transactions(rows):
    frame = pd.DataFrame(rows, columns=["customer_id", "order_id", "order_date", "revenue"])
    frame["order_date"] = pd.to_datetime(frame["order_date"])
    frame["quantity"] = 1
    frame["product_id"] = "P1"
    frame["country"] = "United Kingdom"
    return frame


@pytest.fixture
def five_customers():
    return make_transactions(
        [
            ("A", "1", "2011-12-01", 500.0),
            ("A", "2", "2011-12-05", 500.0),
            ("A", "3", "2011-12-09", 500.0),
            ("B", "4", "2011-11-20", 300.0),
            ("B", "5", "2011-12-02", 300.0),
            ("C", "6", "2011-10-01", 200.0),
            ("D", "7", "2011-06-01", 900.0),
            ("D", "8", "2011-07-01", 900.0),
            ("D", "9", "2011-08-01", 900.0),
            ("E", "10", "2011-01-10", 50.0),
        ]
    )


def test_percentile_score_gives_ties_identical_scores():
    scores = percentile_score(pd.Series([1, 1, 1, 2, 3, 4, 5, 6, 7, 8]), levels=5)
    assert scores.iloc[:3].nunique() == 1
    assert scores.iloc[0] == 1
    assert scores.iloc[-1] == 5
    assert scores.is_monotonic_increasing


def test_percentile_score_lower_is_better():
    scores = percentile_score(pd.Series([10, 20, 30, 40, 50]), levels=5, higher_is_better=False)
    assert list(scores) == [5, 4, 3, 2, 1]


def test_calculate_rfm_metrics(five_customers):
    rfm = calculate_rfm(five_customers).set_index("customer_id")
    assert rfm.loc["A", "recency_days"] == 1
    assert rfm.loc["A", "frequency"] == 3
    assert rfm.loc["A", "monetary"] == pytest.approx(1500.0)
    assert rfm.loc["E", "recency_days"] == (pd.Timestamp("2011-12-10") - pd.Timestamp("2011-01-10")).days
    assert rfm.loc["A", "r_score"] == 5
    assert rfm.loc["E", "r_score"] == 1
    assert rfm.loc["D", "m_score"] == 5
    assert rfm.loc["A", "rfm_cell"] == f"{rfm.loc['A', 'r_score']}{rfm.loc['A', 'f_score']}{rfm.loc['A', 'm_score']}"


def test_fm_score_rounds_half_up(five_customers):
    rfm = calculate_rfm(five_customers)
    expected = ((rfm["f_score"] + rfm["m_score"]) / 2 + 0.5).astype(int)
    assert (rfm["fm_score"] == expected).all()


def test_snapshot_date_excludes_later_orders(five_customers):
    rfm = calculate_rfm(five_customers, RFMConfig(snapshot_date=pd.Timestamp("2011-09-01"))).set_index("customer_id")
    assert set(rfm.index) == {"D", "E"}
    assert rfm.loc["D", "recency_days"] == 31


def test_segments_follow_score_grid():
    r = pd.Series([5, 5, 1, 1, 2, 3, 4])
    fm = pd.Series([5, 1, 5, 1, 3, 3, 2])
    assert list(assign_segments(r, fm)) == [
        "Champions",
        "New Customers",
        "Cannot Lose Them",
        "Hibernating",
        "At Risk",
        "Need Attention",
        "Potential Loyalists",
    ]


def test_default_rules_cover_every_score_pair():
    config = RFMConfig()
    assert len(config.segment_rules) == len(DEFAULT_SEGMENT_RULES)


def test_incomplete_rules_are_rejected():
    with pytest.raises(ValueError):
        RFMConfig(segment_rules=(SegmentRule("Everyone", (1, 5), (1, 4)),))
    with pytest.raises(ValueError):
        RFMConfig(segment_rules=DEFAULT_SEGMENT_RULES + (SegmentRule("Overlap", (5, 5), (5, 5)),))


def test_custom_rules_and_levels(five_customers):
    rules = (SegmentRule("High", (2, 3), (1, 3)), SegmentRule("Low", (1, 1), (1, 3)))
    rfm = calculate_rfm(five_customers, RFMConfig(score_levels=3, segment_rules=rules))
    assert set(rfm["segment"]) <= {"High", "Low"}
    assert rfm[["r_score", "f_score", "m_score"]].max().max() <= 3


def test_summary_and_thresholds_are_consistent(five_customers):
    rfm = calculate_rfm(five_customers)
    summary = segment_summary(rfm)
    assert summary["customers"].sum() == len(rfm)
    assert summary["revenue"].sum() == pytest.approx(rfm["monetary"].sum())
    assert summary["revenue_share"].sum() == pytest.approx(1.0)
    thresholds = score_thresholds(rfm)
    assert set(thresholds["metric"]) == {"recency_days", "frequency", "monetary"}
    assert thresholds.groupby("metric")["customers"].sum().eq(len(rfm)).all()


def test_segment_activity_change_windows(five_customers):
    rfm = calculate_rfm(five_customers)
    activity = segment_activity_change(five_customers, rfm, window_days=70)
    assert activity["recent_revenue"].sum() == pytest.approx(2300.0)
    assert activity["prior_revenue"].sum() == pytest.approx(900.0)
