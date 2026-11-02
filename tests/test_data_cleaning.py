import pytest

from src.data_cleaning import clean_transactions, is_cancellation, validate_clean_transactions


def step_counts(result):
    return dict(zip(result.report()["step"], result.report()["rows_removed"]))


def test_cleaning_steps_remove_expected_rows(cleaning_result):
    counts = step_counts(cleaning_result)
    assert counts["invalid or missing order date"] == 1
    assert counts["missing customer id"] == 3
    assert counts["duplicate lines"] == 1
    assert counts["cancellation invoices"] == 2
    assert counts["non-merchandise codes"] == 1
    assert counts["non-positive quantity"] == 1
    assert counts["non-positive unit price"] == 1
    assert len(cleaning_result.transactions) == 5


def test_clean_output_passes_validation(cleaning_result):
    assert validate_clean_transactions(cleaning_result.transactions) == []


def test_row_accounting_is_consistent(raw_transactions, cleaning_result):
    report = cleaning_result.report()
    assert report["rows_removed"].sum() + len(cleaning_result.transactions) == len(raw_transactions)
    assert report["rows_remaining"].iloc[-1] == len(cleaning_result.transactions)


def test_cancellations_are_kept_separately(cleaning_result):
    cancellations = cleaning_result.cancellations
    assert set(cancellations["order_id"]) == {"C536379", "C536383"}
    assert cancellations["revenue"].sum() == pytest.approx(-27.50 - 4.65)


def test_revenue_and_derived_fields(cleaning_result):
    transactions = cleaning_result.transactions
    assert transactions["revenue"].sum() == pytest.approx(15.30 + 20.34 + 90.0 + 45.0 + 5.5)
    first = transactions.iloc[0]
    assert str(first["order_quarter"]) == "2010Q4"
    assert first["order_month"].day == 1
    assert first["order_day_of_week"] == "Wednesday"


def test_is_cancellation_detects_prefix(raw_transactions):
    flags = is_cancellation(raw_transactions["order_id"])
    assert flags.sum() == 2


def test_validation_flags_problems(cleaning_result):
    broken = cleaning_result.transactions.copy()
    broken.loc[0, "quantity"] = -5
    broken.loc[1, "unit_price"] = 0
    problems = validate_clean_transactions(broken)
    assert "non-positive quantities" in problems
    assert "non-positive unit prices" in problems


def test_missing_columns_raise(raw_transactions):
    with pytest.raises(ValueError):
        clean_transactions(raw_transactions.drop(columns=["country"]))
