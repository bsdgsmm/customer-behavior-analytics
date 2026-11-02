from dataclasses import dataclass, field
from itertools import product

import numpy as np
import pandas as pd

from src.aggregations import build_customer_summary


@dataclass(frozen=True)
class SegmentRule:
    name: str
    recency_scores: tuple[int, int]
    frequency_monetary_scores: tuple[int, int]

    def matches(self, recency_score: pd.Series, frequency_monetary_score: pd.Series) -> pd.Series:
        r_low, r_high = self.recency_scores
        fm_low, fm_high = self.frequency_monetary_scores
        return recency_score.between(r_low, r_high) & frequency_monetary_score.between(fm_low, fm_high)


DEFAULT_SEGMENT_RULES = (
    SegmentRule("Champions", (5, 5), (4, 5)),
    SegmentRule("Loyal Customers", (3, 4), (4, 5)),
    SegmentRule("Potential Loyalists", (4, 5), (2, 3)),
    SegmentRule("New Customers", (5, 5), (1, 1)),
    SegmentRule("Promising", (4, 4), (1, 1)),
    SegmentRule("Need Attention", (3, 3), (3, 3)),
    SegmentRule("About to Sleep", (3, 3), (1, 2)),
    SegmentRule("Cannot Lose Them", (1, 2), (5, 5)),
    SegmentRule("At Risk", (1, 2), (3, 4)),
    SegmentRule("Hibernating", (1, 2), (1, 2)),
)

SEGMENT_ORDER = [rule.name for rule in DEFAULT_SEGMENT_RULES]


@dataclass(frozen=True)
class RFMConfig:
    score_levels: int = 5
    snapshot_date: pd.Timestamp | None = None
    segment_rules: tuple[SegmentRule, ...] = field(default=DEFAULT_SEGMENT_RULES)

    def __post_init__(self):
        if self.score_levels < 2:
            raise ValueError("score_levels must be at least 2")
        levels = range(1, self.score_levels + 1)
        grid = pd.DataFrame(list(product(levels, levels)), columns=["r", "fm"])
        coverage = sum(rule.matches(grid["r"], grid["fm"]).astype(int) for rule in self.segment_rules)
        if not (coverage == 1).all():
            gaps = grid[coverage != 1].to_records(index=False).tolist()
            raise ValueError(f"Segment rules must assign every R and FM score pair exactly once; check {gaps}")


def percentile_score(values: pd.Series, levels: int, higher_is_better: bool = True) -> pd.Series:
    percentile = values.rank(method="min", pct=True, ascending=higher_is_better)
    return np.ceil(percentile * levels).clip(1, levels).astype(int)


def resolve_snapshot_date(transactions: pd.DataFrame, config: RFMConfig) -> pd.Timestamp:
    if config.snapshot_date is not None:
        return pd.Timestamp(config.snapshot_date)
    return transactions["order_date"].max().normalize() + pd.Timedelta(days=1)


def calculate_rfm(transactions: pd.DataFrame, config: RFMConfig = RFMConfig()) -> pd.DataFrame:
    snapshot = resolve_snapshot_date(transactions, config)
    history = transactions[transactions["order_date"] < snapshot]
    if history.empty:
        raise ValueError("No transactions occur before the snapshot date")
    customers = build_customer_summary(history)
    rfm = pd.DataFrame(
        {
            "customer_id": customers["customer_id"],
            "country": customers["country"],
            "last_order_date": customers["last_order_date"],
            "recency_days": (snapshot - customers["last_order_date"].dt.normalize()).dt.days,
            "frequency": customers["orders"],
            "monetary": customers["revenue"],
        }
    )
    levels = config.score_levels
    rfm["r_score"] = percentile_score(-rfm["recency_days"], levels)
    rfm["f_score"] = percentile_score(rfm["frequency"], levels)
    rfm["m_score"] = percentile_score(rfm["monetary"], levels)
    rfm["fm_score"] = np.floor((rfm["f_score"] + rfm["m_score"]) / 2 + 0.5).astype(int)
    rfm["rfm_cell"] = rfm["r_score"].astype(str) + rfm["f_score"].astype(str) + rfm["m_score"].astype(str)
    rfm["rfm_total"] = rfm[["r_score", "f_score", "m_score"]].sum(axis=1)
    rfm["segment"] = assign_segments(rfm["r_score"], rfm["fm_score"], config.segment_rules)
    return rfm.reset_index(drop=True)


def assign_segments(
    recency_score: pd.Series, frequency_monetary_score: pd.Series, rules: tuple[SegmentRule, ...] = DEFAULT_SEGMENT_RULES
) -> pd.Series:
    conditions = [rule.matches(recency_score, frequency_monetary_score) for rule in rules]
    names = [rule.name for rule in rules]
    return pd.Series(np.select(conditions, names, default="Unassigned"), index=recency_score.index)


def score_thresholds(rfm: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric, score in (("recency_days", "r_score"), ("frequency", "f_score"), ("monetary", "m_score")):
        grouped = rfm.groupby(score)[metric].agg(["min", "max", "count"]).reset_index()
        grouped.columns = ["score", "min_value", "max_value", "customers"]
        grouped.insert(0, "metric", metric)
        rows.append(grouped)
    return pd.concat(rows, ignore_index=True)


def segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    summary = (
        rfm.groupby("segment")
        .agg(
            customers=("customer_id", "nunique"),
            revenue=("monetary", "sum"),
            mean_recency_days=("recency_days", "mean"),
            mean_frequency=("frequency", "mean"),
            mean_monetary=("monetary", "mean"),
            median_monetary=("monetary", "median"),
        )
        .reset_index()
    )
    summary["customer_share"] = summary["customers"] / summary["customers"].sum()
    summary["revenue_share"] = summary["revenue"] / summary["revenue"].sum()
    order = {name: position for position, name in enumerate(SEGMENT_ORDER)}
    summary["segment_order"] = summary["segment"].map(order).fillna(len(order))
    return summary.sort_values(["segment_order", "segment"]).drop(columns="segment_order").reset_index(drop=True)


def segment_activity_change(transactions: pd.DataFrame, rfm: pd.DataFrame, window_days: int = 90) -> pd.DataFrame:
    end = transactions["order_date"].max().normalize() + pd.Timedelta(days=1)
    recent_start = end - pd.Timedelta(days=window_days)
    prior_start = recent_start - pd.Timedelta(days=window_days)
    labelled = transactions.merge(rfm[["customer_id", "segment"]], on="customer_id", how="inner")
    windows = {
        "prior": labelled[(labelled["order_date"] >= prior_start) & (labelled["order_date"] < recent_start)],
        "recent": labelled[(labelled["order_date"] >= recent_start) & (labelled["order_date"] < end)],
    }
    frames = []
    for label, frame in windows.items():
        grouped = frame.groupby("segment").agg(
            **{f"{label}_revenue": ("revenue", "sum"), f"{label}_active_customers": ("customer_id", "nunique")}
        )
        frames.append(grouped)
    table = pd.concat(frames, axis=1).reindex(rfm["segment"].unique()).fillna(0)
    table["revenue_change_pct"] = np.where(
        table["prior_revenue"] > 0, table["recent_revenue"] / table["prior_revenue"].replace(0, np.nan) - 1, np.nan
    )
    order = {name: position for position, name in enumerate(SEGMENT_ORDER)}
    table = table.rename_axis("segment").reset_index()
    table["segment_order"] = table["segment"].map(order).fillna(len(order))
    return table.sort_values("segment_order").drop(columns="segment_order").reset_index(drop=True)
