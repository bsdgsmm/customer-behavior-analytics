from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
TABLES_DIR = REPORTS_DIR / "tables"
SQL_DIR = PROJECT_ROOT / "sql"

DATASET_URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
RAW_ARCHIVE_PATH = RAW_DATA_DIR / "online_retail.zip"
RAW_EXCEL_NAME = "Online Retail.xlsx"
RAW_CSV_PATH = RAW_DATA_DIR / "online_retail.csv"
CLEAN_TRANSACTIONS_PATH = PROCESSED_DATA_DIR / "transactions_clean.csv"
CANCELLATIONS_PATH = PROCESSED_DATA_DIR / "cancellations.csv"

SOURCE_COLUMN_MAP = {
    "InvoiceNo": "order_id",
    "StockCode": "product_id",
    "Description": "product_name",
    "Quantity": "quantity",
    "InvoiceDate": "order_date",
    "UnitPrice": "unit_price",
    "CustomerID": "customer_id",
    "Country": "country",
}

REQUIRED_COLUMNS = list(SOURCE_COLUMN_MAP.values())
