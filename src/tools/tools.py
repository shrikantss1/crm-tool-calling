import json
import re
from functools import lru_cache

import pandas as pd

from .metadata import (
    TABLE_PATHS,
    get_columns,
    validate_table,
    validate_column,
)

DEFAULT_ROW_LIMIT = 50
MAX_ROW_LIMIT = 500


@lru_cache(maxsize=8)
def load_table(table: str) -> pd.DataFrame:
    validate_table(table)
    return pd.read_csv(TABLE_PATHS[table])


def _canonicalize_operator(operator: str) -> str:
    op = str(operator).lower().strip()
    if op in {"==", "equals", "eq"}:
        return "eq"
    if op in {"!=", "not_equals", "ne"}:
        return "ne"
    if op in {"contains", "like", "includes"}:
        return "contains"
    if op in {">", "gt"}:
        return "gt"
    if op in {">=", "gte"}:
        return "gte"
    if op in {"<", "lt"}:
        return "lt"
    if op in {"<=", "lte"}:
        return "lte"
    raise ValueError(
        f"Unsupported operator '{operator}'. Valid operators: eq, ne, contains, gt, gte, lt, lte"
    )


def _apply_condition(
    df: pd.DataFrame,
    table: str,
    column: str,
    operator: str,
    value: list,
) -> pd.Series:
    validate_column(table, column)
    op = _canonicalize_operator(operator)
    series = df[column]

    values = [str(v).strip() for v in value if str(v).strip()]
    if not values:
        raise ValueError("At least one filter value must be provided")

    if op == "eq":
        return series.astype(str).isin(values)
    elif op == "ne":
        return ~series.astype(str).isin(values)
    elif op == "contains":
        pattern = "|".join(re.escape(v) for v in values)
        return series.astype(str).str.contains(pattern, case=False, na=False)
    elif op in {"gt", "gte", "lt", "lte"}:
        if len(values) != 1:
            raise ValueError(
                f"Operator '{operator}' requires exactly one value for numeric comparison. "
                "For a range, use two ANDed conditions (e.g., close_value > 100 AND close_value < 1000)."
            )
        try:
            threshold = pd.to_numeric(values[0], errors="raise")
        except (ValueError, TypeError):
            raise ValueError(f"Value '{values[0]}' is not numeric for operator '{operator}'")

        numeric_series = pd.to_numeric(series, errors="coerce")
        if numeric_series.isna().all() and not series.isna().all():
            raise ValueError(
                f"Column '{column}' could not be coerced to numeric for operator '{operator}'"
            )

        if op == "gt":
            return numeric_series > threshold
        elif op == "gte":
            return numeric_series >= threshold
        elif op == "lt":
            return numeric_series < threshold
        elif op == "lte":
            return numeric_series <= threshold

    return pd.Series(False, index=df.index)


def filter_dataframe(
    table: str,
    conditions: list[dict] | None = None,
) -> pd.DataFrame:
    validate_table(table)
    df = load_table(table)
    mask = pd.Series(True, index=df.index)

    for cond in conditions or []:
        cond_mask = _apply_condition(
            df,
            table,
            cond["column"],
            cond["operator"],
            cond["value"],
        )
        mask &= cond_mask

    return df[mask].copy()


def query_crm_data(
    table: str,
    conditions: list[dict] | None = None,
    limit: int | None = None,
) -> dict:
    print("Querying CRM data for table=%s with conditions=%s and limit=%s", table, conditions, limit)
    filtered = filter_dataframe(table, conditions)
    effective_limit = max(1, min(limit or DEFAULT_ROW_LIMIT, MAX_ROW_LIMIT))
    total_matches = len(filtered)
    page = filtered.head(effective_limit)
    rows = json.loads(page.to_json(orient="records"))

    return {
        "table": table,
        "total_matches": total_matches,
        "returned_count": len(rows),
        "truncated": total_matches > len(rows),
        "limit_applied": effective_limit,
        "rows": rows,
    }
