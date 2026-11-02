import argparse
import json
from pathlib import Path

import pandas as pd

from src import visualization as charts
from src.config import PROJECT_ROOT, REPORTS_DIR, TABLES_DIR
from src.data_cleaning import clean_transactions, save_cleaning_outputs, validate_clean_transactions
from src.data_loader import load_raw_transactions
from src.exploratory_analysis import order_frequency_distribution, product_performance, summary_kpis, top_products
from src.retention_analysis import (
    average_retention_curve,
    cohort_cumulative_revenue_per_customer,
    cohort_retention,
    customer_type_breakdown,
    days_to_second_order,
    lifetime_revenue_statistics,
    monthly_customer_activity,
    repeat_purchase_summary,
)
from src.revenue_analysis import (
    country_performance,
    month_coverage,
    pareto_curve,
    revenue_by_period,
    revenue_concentration,
    top_customers,
)
from src.rfm_analysis import (
    DEFAULT_RFM_CONFIG,
    SEGMENT_ORDER,
    RFMConfig,
    calculate_rfm,
    resolve_snapshot_date,
    score_thresholds,
    segment_activity_change,
    segment_summary,
)
from src.sql_analysis import export_sql_results, run_all_sql

SUMMARY_PATH = REPORTS_DIR / "summary_metrics.json"


class DataValidationError(RuntimeError):
    pass


def _month_label(month: pd.Timestamp) -> str:
    return month.strftime("%B %Y")


def _write_tables(tables: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(output_dir / f"{name}.csv", index=table.index.name is not None)


def _round_floats(value):
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, dict):
        return {key: _round_floats(item) for key, item in value.items()}
    return value


def run_pipeline(download: bool = True, rfm_config: RFMConfig = DEFAULT_RFM_CONFIG) -> dict:
    raw = load_raw_transactions(download=download)
    cleaning = clean_transactions(raw)
    problems = validate_clean_transactions(cleaning.transactions)
    if problems:
        raise DataValidationError(f"Cleaned data failed validation: {problems}")
    save_cleaning_outputs(cleaning)
    transactions = cleaning.transactions

    coverage = month_coverage(transactions)
    partial_months = coverage.loc[coverage["is_partial_month"], "month"]
    complete_transactions = transactions[~transactions["order_month"].isin(partial_months)]

    monthly = revenue_by_period(transactions, "month").merge(
        coverage[["month", "trading_days", "is_partial_month"]], on="month"
    )
    quarterly = revenue_by_period(transactions, "quarter")
    products = product_performance(transactions)
    rfm = calculate_rfm(transactions, rfm_config)
    segments = segment_summary(rfm)
    activity = monthly_customer_activity(transactions)
    breakdown = customer_type_breakdown(transactions)
    retention = cohort_retention(complete_transactions)
    countries = country_performance(transactions)
    concentration = revenue_concentration(transactions)
    second_order_days = days_to_second_order(transactions)

    tables = {
        "cleaning_report": cleaning.report(),
        "monthly_revenue": monthly,
        "quarterly_revenue": quarterly,
        "top_products_by_revenue": top_products(transactions, "revenue", 10),
        "top_products_by_units": top_products(transactions, "units_sold", 10),
        "top_products_by_orders": top_products(transactions, "orders", 10),
        "order_frequency_distribution": order_frequency_distribution(transactions),
        "country_performance": countries,
        "top_customers": top_customers(transactions, 10),
        "revenue_concentration": concentration,
        "rfm_score_thresholds": score_thresholds(rfm),
        "rfm_segment_summary": segments,
        "rfm_segment_activity_change": segment_activity_change(transactions, rfm),
        "customer_type_breakdown": breakdown,
        "monthly_customer_activity": activity,
        "cohort_retention": retention,
        "cohort_average_retention": average_retention_curve(complete_transactions),
        "cohort_cumulative_revenue_per_customer": cohort_cumulative_revenue_per_customer(complete_transactions),
    }
    _write_tables(tables, TABLES_DIR)
    export_sql_results(run_all_sql(transactions), TABLES_DIR / "sql")

    charts.apply_style()
    partial_note = ", ".join(
        f"{_month_label(row.month)} covers {row.first_day:%d %b}-{row.last_day:%d %b} only"
        for row in coverage[coverage["is_partial_month"]].itertuples()
    )
    complete_months = coverage.loc[~coverage["is_partial_month"], "month"]
    cohort_note = (
        f"Complete months only ({_month_label(complete_months.min())} to {_month_label(complete_months.max())}); "
        "blank cells are not yet observable"
    )
    figures = [
        charts.plot_monthly_revenue(
            monthly, partial_months, f"Revenue after cleaning; {partial_note or 'all months complete'}"
        ),
        charts.plot_new_vs_returning_customers(activity),
        charts.plot_segment_distribution(segments),
        charts.plot_revenue_by_segment(segments),
        charts.plot_repeat_vs_one_time(breakdown),
        charts.plot_rfm_segment_comparison(rfm, SEGMENT_ORDER),
        charts.plot_top_products(products.head(10)),
        charts.plot_country_revenue(countries),
        charts.plot_revenue_concentration(pareto_curve(transactions)),
        charts.plot_cohort_retention(retention, cohort_note),
    ]

    summary = {
        "kpis": summary_kpis(transactions),
        "cancellations": {
            "cancellation_lines": len(cleaning.cancellations),
            "cancelled_value": round(float(-cleaning.cancellations["revenue"].sum()), 2),
        },
        "repeat_purchases": repeat_purchase_summary(transactions),
        "days_to_second_order": {
            "median": float(second_order_days.median()),
            "mean": float(second_order_days.mean()),
        },
        "lifetime_revenue": lifetime_revenue_statistics(transactions),
        "rfm_snapshot_date": resolve_snapshot_date(transactions, rfm_config).strftime("%Y-%m-%d"),
        "partial_months": [month.strftime("%Y-%m") for month in partial_months],
        "figures": [path.relative_to(PROJECT_ROOT).as_posix() for path in figures],
    }
    summary = _round_floats(summary)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the customer behavior analytics pipeline.")
    parser.add_argument("--no-download", action="store_true", help="fail instead of downloading missing raw data")
    arguments = parser.parse_args()
    run_pipeline(download=not arguments.no_download)


if __name__ == "__main__":
    main()
