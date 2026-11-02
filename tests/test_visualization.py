import matplotlib.pyplot as plt
import pytest

from src import visualization as charts
from src.exploratory_analysis import product_performance
from src.retention_analysis import cohort_retention, customer_type_breakdown, monthly_customer_activity
from src.revenue_analysis import country_performance, month_coverage, pareto_curve, revenue_by_period
from src.rfm_analysis import SEGMENT_ORDER, calculate_rfm, segment_summary


@pytest.fixture
def transactions(cleaning_result):
    return cleaning_result.transactions


def test_currency_formatting():
    assert charts.format_currency(1_234_567) == "£1.2M"
    assert charts.format_currency(2_600) == "£2.6K"
    assert charts.format_currency(45_000) == "£45K"
    assert charts.format_currency(480.3) == "£480"


def test_all_charts_render(tmp_path, transactions):
    charts.apply_style()
    rfm = calculate_rfm(transactions)
    segments = segment_summary(rfm)
    coverage = month_coverage(transactions)
    paths = [
        charts.plot_monthly_revenue(
            revenue_by_period(transactions), coverage.loc[coverage["is_partial_month"], "month"], "note", tmp_path
        ),
        charts.plot_new_vs_returning_customers(monthly_customer_activity(transactions), tmp_path),
        charts.plot_segment_distribution(segments, tmp_path),
        charts.plot_revenue_by_segment(segments, tmp_path),
        charts.plot_repeat_vs_one_time(customer_type_breakdown(transactions), tmp_path),
        charts.plot_rfm_segment_comparison(rfm, SEGMENT_ORDER, tmp_path),
        charts.plot_top_products(product_performance(transactions).head(3), tmp_path),
        charts.plot_country_revenue(country_performance(transactions), 2, tmp_path),
        charts.plot_revenue_concentration(pareto_curve(transactions), tmp_path),
        charts.plot_cohort_retention(cohort_retention(transactions), "note", tmp_path),
    ]
    assert len({path.name for path in paths}) == len(paths)
    assert all(path.exists() and path.stat().st_size > 10_000 for path in paths)
    assert plt.get_fignums() == []
