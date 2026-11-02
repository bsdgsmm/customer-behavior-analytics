import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from src.config import (
    DATASET_URL,
    RAW_ARCHIVE_PATH,
    RAW_CSV_PATH,
    RAW_EXCEL_NAME,
    REQUIRED_COLUMNS,
    SOURCE_COLUMN_MAP,
)


class DatasetError(RuntimeError):
    pass


def download_dataset(url: str = DATASET_URL, destination: Path = RAW_ARCHIVE_PATH, timeout: int = 120) -> Path:
    destination = Path(destination)
    if destination.exists() and destination.stat().st_size > 0:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response, open(temporary, "wb") as handle:
            while chunk := response.read(1 << 20):
                handle.write(chunk)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise DatasetError(f"Could not download the dataset from {url}: {error}") from error
    temporary.replace(destination)
    return destination


def convert_archive_to_csv(
    archive_path: Path = RAW_ARCHIVE_PATH,
    csv_path: Path = RAW_CSV_PATH,
    member_name: str = RAW_EXCEL_NAME,
) -> Path:
    archive_path, csv_path = Path(archive_path), Path(csv_path)
    if csv_path.exists() and csv_path.stat().st_mtime >= archive_path.stat().st_mtime:
        return csv_path
    try:
        with zipfile.ZipFile(archive_path) as archive, archive.open(member_name) as workbook:
            frame = pd.read_excel(workbook, dtype={"InvoiceNo": str, "StockCode": str})
    except (zipfile.BadZipFile, KeyError) as error:
        raise DatasetError(f"{archive_path} is not a valid Online Retail archive: {error}") from error
    frame.to_csv(csv_path, index=False)
    return csv_path


def standardize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in SOURCE_COLUMN_MAP if column not in frame.columns]
    if missing:
        raise DatasetError(f"Source data is missing expected columns: {missing}")
    standardized = frame.rename(columns=SOURCE_COLUMN_MAP)[REQUIRED_COLUMNS].copy()
    standardized["order_id"] = standardized["order_id"].astype("string").str.strip()
    standardized["product_id"] = standardized["product_id"].astype("string").str.strip().str.upper()
    standardized["product_name"] = standardized["product_name"].astype("string").str.strip()
    standardized["country"] = standardized["country"].astype("string").str.strip()
    customer_numeric = pd.to_numeric(standardized["customer_id"], errors="coerce")
    standardized["customer_id"] = customer_numeric.astype("Int64").astype("string")
    standardized["quantity"] = pd.to_numeric(standardized["quantity"], errors="coerce")
    standardized["unit_price"] = pd.to_numeric(standardized["unit_price"], errors="coerce")
    standardized["order_date"] = pd.to_datetime(standardized["order_date"], errors="coerce")
    return standardized


def load_raw_transactions(csv_path: Path = RAW_CSV_PATH, download: bool = True) -> pd.DataFrame:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        if not download:
            raise DatasetError(f"Raw data not found at {csv_path}. Run the pipeline with download enabled.")
        convert_archive_to_csv(download_dataset(), csv_path)
    raw = pd.read_csv(csv_path, dtype={"InvoiceNo": str, "StockCode": str, "Description": str, "Country": str})
    return standardize_columns(raw)
