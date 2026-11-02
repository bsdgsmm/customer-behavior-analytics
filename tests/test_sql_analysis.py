import pandas as pd
import pytest

from src.aggregations import build_customer_summary
from src.config import SQL_DIR
from src.retention_analysis import cohort_counts, repeat_purchase_summary
from src.revenue_analysis import country_performance, revenue_by_period, revenue_concentration
from src.rfm_analysis import calculate_rfm
from src.sql_analysis import SQL_FILES, export_sql_results, run_all_sql, view_names


@pytest.fixture
def transactions(cleaning_result):
    return cleaning_result.transactions


@pytest.fixture
def sql_results(transactions):
    return run_all_sql(transactions)


def test_every_declared_view_returns_a_result(sql_results):
    declared = [name for file_name in SQL_FILES for name in view_names((SQL_DIR / file_name).read_text())]
    assert sorted(sql_results) == sorted(declared)


def test_monthly_revenue_matches_pandas(transactions, sql_results):
    pandas_monthly = revenue_by_period(transactions, "month")
    sql_monthly = sql_results["monthly_revenue"]
    assert sql_monthly["revenue"].tolist() == pytest.approx(pandas_monthly["revenue"].round(2).tolist())
    assert sql_monthly["orders"].tolist() == pandas_monthly["orders"].tolist()


def test_quarterly_and_country_revenue_match(transactions, sql_results):
    quarterly = revenue_by_period(transactions, "quarter")
    assert sql_results["quarterly_revenue"]["quarter"].tolist() == quarterly["quarter"].tolist()
    countries = country_performance(transactions).set_index("country")["revenue"]
    sql_countries = sql_results["country_revenue"].set_index("country")["revenue"]
    assert sql_countries.sort_index().tolist() == pytest.approx(countries.sort_index().round(2).tolist())


def test_customer_summary_matches_pandas(transactions, sql_results):
    pandas_summary = build_customer_summary(transactions).set_index("customer_id")
    sql_summary = sql_results["customer_summary"].set_index("customer_id").loc[pandas_summary.index]
    assert sql_summary["orders"].tolist() == pandas_summary["orders"].tolist()
    assert sql_summary["revenue"].tolist() == pytest.approx(pandas_summary["revenue"].round(2).tolist())


def test_repeat_metrics_match_pandas(transactions, sql_results):
    pandas_metrics = repeat_purchase_summary(transactions)
    sql_metrics = sql_results["repeat_purchase_metrics"].iloc[0]
    assert sql_metrics["repeat_customers"] == pandas_metrics["repeat_customers"]
    assert sql_metrics["repeat_purchase_rate"] == pytest.approx(pandas_metrics["repeat_purchase_rate"], abs=1e-4)


def test_rfm_scores_match_pandas(transactions, sql_results):
    pandas_rfm = calculate_rfm(transactions).set_index("customer_id")
    sql_rfm = sql_results["rfm_scores"].set_index("customer_id").loc[pandas_rfm.index]
    for column in ("recency_days", "frequency", "r_score", "f_score", "m_score"):
        assert sql_rfm[column].tolist() == pandas_rfm[column].tolist()


def test_cohort_retention_matches_pandas(transactions, sql_results):
    counts = cohort_counts(transactions).stack()
    counts = counts[counts > 0].astype(int)
    sql_cohorts = sql_results["cohort_retention"]
    sql_cohorts = sql_cohorts.assign(cohort_month=pd.to_datetime(sql_cohorts["cohort_month"]))
    sql_counts = sql_cohorts.set_index(["cohort_month", "months_since_acquisition"])["active_customers"]
    assert sql_counts.to_dict() == counts.to_dict()


def test_export_writes_csv_files(tmp_path, sql_results):
    paths = export_sql_results(sql_results, tmp_path)
    assert len(paths) == len(sql_results) - 1
    assert not (tmp_path / "orders.csv").exists()
    assert all(path.exists() and path.stat().st_size > 0 for path in paths)


def test_revenue_concentration_matches_pandas(transactions, sql_results):
    pandas_table = revenue_concentration(transactions)
    sql_table = sql_results["revenue_concentration"]
    assert sql_table["customers"].tolist() == pandas_table["customers"].tolist()
    assert sql_table["revenue"].tolist() == pytest.approx(pandas_table["revenue"].round(2).tolist())
