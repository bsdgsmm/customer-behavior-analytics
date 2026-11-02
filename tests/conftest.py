import pandas as pd
import pytest


def _raw_rows():
    return [
        ("536365", "85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 6, "2010-12-01 08:26", 2.55, 17850.0, "United Kingdom"),
        ("536365", "71053", "WHITE METAL LANTERN", 6, "2010-12-01 08:26", 3.39, 17850.0, "United Kingdom"),
        ("536365", "71053", "WHITE METAL LANTERN", 6, "2010-12-01 08:26", 3.39, 17850.0, "United Kingdom"),
        ("C536379", "D", "Discount", -1, "2010-12-01 09:41", 27.50, 14527.0, "United Kingdom"),
        ("536380", "35004C", "SET OF 3 COLOURED  FLYING DUCKS", 1, "2010-12-01 09:00", 4.65, 15311.0, "United Kingdom"),
        ("C536383", "35004C", "SET OF 3 COLOURED  FLYING DUCKS", -1, "2010-12-01 09:49", 4.65, 15311.0, "United Kingdom"),
        ("536414", "22139", None, 56, "2010-12-01 11:52", 0.0, None, "United Kingdom"),
        ("536544", "21773", "DECORATIVE ROSE BATHROOM BOTTLE", 1, "2010-12-01 14:32", 2.51, None, "United Kingdom"),
        ("536370", "22728", "ALARM CLOCK BAKELIKE PINK", 24, "2010-12-01 08:45", 3.75, 12583.0, "France"),
        ("536370", "POST", "POSTAGE", 3, "2010-12-01 08:45", 18.0, 12583.0, "France"),
        ("537000", "22728", "ALARM CLOCK BAKELIKE PINK", 12, "2011-01-15 10:00", 3.75, 12583.0, "France"),
        ("538000", "21212", "PACK OF 72 RETROSPOT CAKE CASES", 10, "2011-02-20 12:00", 0.55, 15311.0, "United Kingdom"),
        ("539000", "21212", "PACK OF 72 RETROSPOT CAKE CASES", 0, "2011-02-21 12:00", 0.55, 15311.0, "United Kingdom"),
        ("A563185", "B", "Adjust bad debt", 1, "2011-08-12 14:50", 11062.06, None, "United Kingdom"),
        ("540000", "22423", "REGENCY CAKESTAND 3 TIER", 2, "not a date", 12.75, 15311.0, "United Kingdom"),
        ("541000", "22423", "REGENCY CAKESTAND 3 TIER", 1, "2011-03-05 09:00", -12.75, 12583.0, "France"),
    ]


@pytest.fixture
def raw_source_frame():
    columns = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]
    return pd.DataFrame(_raw_rows(), columns=columns)


@pytest.fixture
def raw_transactions(raw_source_frame):
    from src.data_loader import standardize_columns

    return standardize_columns(raw_source_frame)


@pytest.fixture
def cleaning_result(raw_transactions):
    from src.data_cleaning import clean_transactions

    return clean_transactions(raw_transactions)
