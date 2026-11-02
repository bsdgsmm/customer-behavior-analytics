from dataclasses import dataclass, field

import pandas as pd

from src.config import CANCELLATIONS_PATH, CLEAN_TRANSACTIONS_PATH, REQUIRED_COLUMNS

NON_MERCHANDISE_CODES = frozenset(
    {"POST", "DOT", "M", "C2", "D", "S", "BANK CHARGES", "AMAZONFEE", "CRUK", "B"}
)
CANCELLATION_PREFIX = "C"


@dataclass
class CleaningResult:
    transactions: pd.DataFrame
    cancellations: pd.DataFrame
    steps: list[dict] = field(default_factory=list)

    def report(self) -> pd.DataFrame:
        return pd.DataFrame(self.steps, columns=["step", "rows_removed", "rows_remaining"])


class _StepRecorder:
    def __init__(self, frame: pd.DataFrame):
        self.frame = frame
        self.steps = [{"step": "raw rows", "rows_removed": 0, "rows_remaining": len(frame)}]

    def drop(self, step: str, mask: pd.Series) -> pd.DataFrame:
        removed = self.frame[mask]
        self.frame = self.frame[~mask]
        self.steps.append({"step": step, "rows_removed": int(mask.sum()), "rows_remaining": len(self.frame)})
        return removed


def validate_schema(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Transactions are missing required columns: {missing}")


def is_cancellation(order_ids: pd.Series) -> pd.Series:
    return order_ids.astype("string").str.upper().str.startswith(CANCELLATION_PREFIX).fillna(False).astype(bool)


def canonical_product_names(frame: pd.DataFrame) -> pd.Series:
    named = frame.dropna(subset=["product_name"])
    counts = named.groupby(["product_id", "product_name"]).size().rename("lines").reset_index()
    counts = counts.sort_values(["product_id", "lines", "product_name"], ascending=[True, False, True])
    return counts.drop_duplicates("product_id").set_index("product_id")["product_name"]


def add_derived_fields(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    enriched["revenue"] = (enriched["quantity"] * enriched["unit_price"]).round(2)
    enriched["order_month"] = enriched["order_date"].dt.to_period("M").dt.to_timestamp()
    enriched["order_quarter"] = enriched["order_date"].dt.to_period("Q").astype(str)
    enriched["order_day_of_week"] = enriched["order_date"].dt.day_name()
    enriched["order_hour"] = enriched["order_date"].dt.hour
    return enriched


def clean_transactions(
    raw: pd.DataFrame,
    non_merchandise_codes: frozenset[str] = NON_MERCHANDISE_CODES,
) -> CleaningResult:
    validate_schema(raw)
    recorder = _StepRecorder(raw[REQUIRED_COLUMNS].copy())
    frame = recorder.frame
    recorder.drop("invalid or missing order date", frame["order_date"].isna())
    frame = recorder.frame
    recorder.drop("non-numeric quantity or unit price", frame["quantity"].isna() | frame["unit_price"].isna())
    frame = recorder.frame
    recorder.drop("missing customer id", frame["customer_id"].isna())
    names = canonical_product_names(recorder.frame)
    recorder.frame["product_name"] = recorder.frame["product_id"].map(names).fillna("UNKNOWN PRODUCT")
    frame = recorder.frame
    recorder.drop("duplicate lines", frame.duplicated(keep="first"))
    frame = recorder.frame
    cancellations = recorder.drop("cancellation invoices", is_cancellation(frame["order_id"]))
    frame = recorder.frame
    recorder.drop("non-merchandise codes", frame["product_id"].isin(non_merchandise_codes))
    frame = recorder.frame
    recorder.drop("non-positive quantity", frame["quantity"] <= 0)
    frame = recorder.frame
    recorder.drop("non-positive unit price", frame["unit_price"] <= 0)
    cleaned = recorder.frame.copy()
    cleaned["quantity"] = cleaned["quantity"].astype("int64")
    cleaned = add_derived_fields(cleaned).sort_values(["order_date", "order_id"]).reset_index(drop=True)
    cancellations = cancellations.assign(revenue=(cancellations["quantity"] * cancellations["unit_price"]).round(2))
    return CleaningResult(cleaned, cancellations.reset_index(drop=True), recorder.steps)


def validate_clean_transactions(frame: pd.DataFrame) -> list[str]:
    problems = []
    if frame["customer_id"].isna().any():
        problems.append("missing customer ids")
    if (frame["quantity"] <= 0).any():
        problems.append("non-positive quantities")
    if (frame["unit_price"] <= 0).any():
        problems.append("non-positive unit prices")
    if frame["order_date"].isna().any():
        problems.append("missing order dates")
    if is_cancellation(frame["order_id"]).any():
        problems.append("cancellation invoices present")
    if frame.duplicated(subset=REQUIRED_COLUMNS).any():
        problems.append("duplicate lines present")
    if (frame.groupby("order_id")["customer_id"].nunique() > 1).any():
        problems.append("orders mapped to several customers")
    return problems


def save_cleaning_outputs(result: CleaningResult) -> None:
    CLEAN_TRANSACTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.transactions.to_csv(CLEAN_TRANSACTIONS_PATH, index=False)
    result.cancellations.to_csv(CANCELLATIONS_PATH, index=False)


def load_clean_transactions(path=CLEAN_TRANSACTIONS_PATH) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        dtype={"order_id": "string", "product_id": "string", "customer_id": "string", "product_name": "string", "country": "string"},
        parse_dates=["order_date", "order_month"],
    )
    return frame
