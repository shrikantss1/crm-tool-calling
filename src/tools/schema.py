from .metadata import get_table_names, get_columns, get_column_description
from .tools import DEFAULT_ROW_LIMIT, MAX_ROW_LIMIT


def build_tool_schema() -> dict:
    table_block = "\n".join(
        f"- {t}: " + ", ".join(f"{c} ({get_column_description(t, c)})" for c in get_columns(t))
        for t in get_table_names()
    )

    return {
        "type": "function",
        "name": "query_crm_data",
        "description": (
            "Query the CRM's tabular data (accounts, products, sales_pipeline, sales_teams) "
            "with one or more filter conditions ANDed together. Use this whenever the user "
            "asks about specific accounts, deals, products, or sales agents.\n\n"
            "Tables and columns:\n" + table_block
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "table": {
                    "type": "string",
                    "enum": get_table_names(),
                    "description": "Which table to query.",
                },
                "conditions": {
                    "type": "array",
                    "description": (
                        "Filter conditions combined with AND. Omit for all rows. For a numeric "
                        "range use two conditions on the same column, e.g. "
                        '{"column":"close_value","operator":"gt","value":["100"]} AND '
                        '{"column":"close_value","operator":"lt","value":["1000"]}.'
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "column": {
                                "type": "string",
                                "description": "Must be valid for the chosen table.",
                            },
                            "operator": {
                                "type": "string",
                                "enum": ["eq", "ne", "contains", "gt", "gte", "lt", "lte"],
                                "description": (
                                    "eq/ne: exact match against any value. contains: case-insensitive "
                                    "substring match. gt/gte/lt/lte: numeric comparison, value must have exactly one entry."
                                ),
                            },
                            "value": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Values to compare against, always an array even for one value.",
                            },
                        },
                        "required": ["column", "operator", "value"],
                    },
                },
                "limit": {
                    "type": "integer",
                    "description": f"Max rows to return (default {DEFAULT_ROW_LIMIT}, hard-capped at {MAX_ROW_LIMIT}).",
                },
            },
            "required": ["table"],
        },
    }
