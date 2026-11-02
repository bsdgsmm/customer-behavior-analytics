import re
from pathlib import Path

import duckdb
import pandas as pd

from src.config import SQL_DIR, TABLES_DIR

SQL_FILES = ("customer_metrics.sql", "revenue_analysis.sql")
VIEW_PATTERN = re.compile(r"CREATE\s+OR\s+REPLACE\s+VIEW\s+(\w+)", re.IGNORECASE)
TRANSACTION_COLUMNS = ["order_id", "customer_id", "order_date", "product_id", "product_name", "quantity", "revenue", "country"]


def create_connection(transactions: pd.DataFrame) -> duckdb.DuckDBPyConnection:
    missing = [column for column in TRANSACTION_COLUMNS if column not in transactions.columns]
    if missing:
        raise ValueError(f"Transactions are missing columns required by the SQL views: {missing}")
    connection = duckdb.connect(database=":memory:")
    frame = transactions[TRANSACTION_COLUMNS].copy()
    for column in ("order_id", "customer_id", "product_id", "product_name", "country"):
        frame[column] = frame[column].astype(object)
    connection.register("transactions_frame", frame)
    connection.execute("CREATE TABLE transactions AS SELECT * FROM transactions_frame")
    connection.unregister("transactions_frame")
    return connection


def view_names(sql_text: str) -> list[str]:
    return VIEW_PATTERN.findall(sql_text)


def run_sql_file(connection: duckdb.DuckDBPyConnection, path: Path) -> dict[str, pd.DataFrame]:
    sql_text = Path(path).read_text(encoding="utf-8")
    try:
        connection.execute(sql_text)
    except duckdb.Error as error:
        raise RuntimeError(f"Failed to execute {Path(path).name}: {error}") from error
    return {name: connection.execute(f"SELECT * FROM {name}").df() for name in view_names(sql_text)}


def run_all_sql(transactions: pd.DataFrame, sql_dir: Path = SQL_DIR) -> dict[str, pd.DataFrame]:
    connection = create_connection(transactions)
    try:
        results = {}
        for file_name in SQL_FILES:
            results.update(run_sql_file(connection, Path(sql_dir) / file_name))
        return results
    finally:
        connection.close()


def export_sql_results(results: dict[str, pd.DataFrame], output_dir: Path = TABLES_DIR / "sql") -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, frame in results.items():
        path = output_dir / f"{name}.csv"
        frame.to_csv(path, index=False)
        paths.append(path)
    return paths
