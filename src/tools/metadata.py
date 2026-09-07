import pandas as pd
from functools import lru_cache

TABLE_PATHS: dict[str, str] = {
    "accounts": "datasets/accounts.csv",
    "products": "datasets/products.csv",
    "sales_pipeline": "datasets/sales_pipeline.csv",
    "sales_teams": "datasets/sales_teams.csv",
}
METADATA_CSV_PATH = "datasets/metadata.csv"


@lru_cache(maxsize=1)
def load_metadata() -> pd.DataFrame:
    df = pd.read_csv(METADATA_CSV_PATH)
    valid_tables = set(TABLE_PATHS.keys())
    metadata_tables = set(df["Table"].unique())
    assert valid_tables == metadata_tables, (
        f"TABLE_PATHS and metadata.csv tables mismatch. "
        f"TABLE_PATHS: {valid_tables}, metadata.csv: {metadata_tables}"
    )
    return df


@lru_cache(maxsize=1)
def _columns_by_table() -> dict[str, list[str]]:
    metadata = load_metadata()
    result = {}
    for table in get_table_names():
        cols = metadata[metadata["Table"] == table]["Field"].tolist()
        result[table] = cols
    return result


@lru_cache(maxsize=1)
def _descriptions() -> dict[tuple[str, str], str]:
    metadata = load_metadata()
    result = {}
    for _, row in metadata.iterrows():
        key = (row["Table"], row["Field"])
        result[key] = row["Description"]
    return result


def get_table_names() -> list[str]:
    return list(TABLE_PATHS.keys())


def get_columns(table: str) -> list[str]:
    validate_table(table)
    return _columns_by_table()[table]


def get_column_description(table: str, column: str) -> str:
    validate_column(table, column)
    descs = _descriptions()
    return descs.get((table, column), "")


def validate_table(table: str) -> None:
    valid = get_table_names()
    if table not in valid:
        raise ValueError(f"Table '{table}' not found. Valid tables: {', '.join(valid)}")


def validate_column(table: str, column: str) -> None:
    validate_table(table)
    valid = get_columns(table)
    if column not in valid:
        raise ValueError(f"Column '{column}' not found in table '{table}'. Valid columns: {', '.join(valid)}")
