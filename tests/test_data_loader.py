import zipfile

import pandas as pd
import pytest

from src.config import REQUIRED_COLUMNS
from src.data_loader import DatasetError, convert_archive_to_csv, load_raw_transactions, standardize_columns


def test_standardize_columns_renames_and_types(raw_source_frame):
    standardized = standardize_columns(raw_source_frame)
    assert list(standardized.columns) == REQUIRED_COLUMNS
    assert standardized.loc[0, "customer_id"] == "17850"
    assert standardized["customer_id"].isna().sum() == 3
    assert pd.api.types.is_datetime64_any_dtype(standardized["order_date"])
    assert standardized["order_date"].isna().sum() == 1


def test_standardize_columns_rejects_missing_columns(raw_source_frame):
    with pytest.raises(DatasetError):
        standardize_columns(raw_source_frame.drop(columns=["UnitPrice"]))


def test_archive_round_trip(tmp_path, raw_source_frame):
    workbook_path = tmp_path / "Online Retail.xlsx"
    raw_source_frame.to_excel(workbook_path, index=False)
    archive_path = tmp_path / "online_retail.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write(workbook_path, arcname="Online Retail.xlsx")
    csv_path = convert_archive_to_csv(archive_path, tmp_path / "online_retail.csv")
    loaded = load_raw_transactions(csv_path, download=False)
    assert len(loaded) == len(raw_source_frame)
    assert loaded.loc[1, "product_id"] == "71053"


def test_missing_raw_file_without_download(tmp_path):
    with pytest.raises(DatasetError):
        load_raw_transactions(tmp_path / "absent.csv", download=False)
