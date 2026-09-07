# CRM Chatbot Tool-Calling Implementation

## Overview

This document summarizes the generalized CRM data-filter tool implementation that enables an LLM to query 4 CRM tables (`accounts`, `products`, `sales_pipeline`, `sales_teams`) with flexible, multi-condition filtering through a single unified tool.

## Architecture

### File Structure

```
src/
├── tools/
│   ├── __init__.py      — Package exports for public API
│   ├── metadata.py      — Table/column registry and validation (data dictionary)
│   ├── tools.py         — Generalized loader, filter engine, and tool entry point
│   └── schema.py        — Builds JSON tool schema for the LLM
└── agent.py             — LLM dispatch loop, tool registry, CLI entrypoint
```

### Key Design Decisions

1. **Single Generic Tool**: `query_crm_data(table, conditions, limit)` handles all 4 tables instead of separate per-table functions.

2. **Metadata-Driven**: `datasets/metadata.csv` is the single source of truth for:
   - Valid table and column names
   - Column descriptions (used in LLM tool schema)
   - Validation at runtime

3. **Multi-Condition Filtering**: Conditions are a list, ANDed together:
   ```python
   conditions = [
       {"column": "deal_stage", "operator": "eq", "value": ["Won"]},
       {"column": "close_value", "operator": ">", "value": ["1000"]},
   ]
   ```

4. **Operator Set** (cleaned up from original):
   - `eq` / `==` / `equals` — exact string match (multiple values supported)
   - `ne` / `!=` / `not_equals` — inverse of eq
   - `contains` / `like` / `includes` — case-insensitive substring (multiple values via OR)
   - `gt` / `>`, `gte` / `>=`, `lt` / `<`, `lte` / `<=` — numeric comparison (exactly one value; ranges use two ANDed conditions)

5. **Error Handling**: Filter functions raise `ValueError` for invalid input; the dispatch loop catches these and formats them as tool error responses the LLM can see and retry from.

6. **Result Serialization**:
   - Hard limit: max 500 rows returned, regardless of `limit` argument (prevents context blowup on large tables like sales_pipeline with 8800 rows)
   - Default limit: 50 rows
   - Response includes: `total_matches`, `returned_count`, `truncated` flag, `rows` array

## Usage

### Direct Python Usage (no LLM)

```python
from src.tools import query_crm_data

# Query: which deals did Moses Frase win over $1000?
result = query_crm_data(
    table="sales_pipeline",
    conditions=[
        {"column": "sales_agent", "operator": "eq", "value": ["Moses Frase"]},
        {"column": "deal_stage", "operator": "eq", "value": ["Won"]},
        {"column": "close_value", "operator": "gt", "value": ["1000"]},
    ],
    limit=10
)

print(result["total_matches"])  # 15
print(result["returned_count"]) # 10
print(result["rows"][0])        # First matching deal
```

### With LLM (Agent Loop)

```bash
cd /Users/shrikantsavadatti/repos/tool-calling
export OLLAMA_BASE_URL=http://localhost:11434/v1
export OLLAMA_API_KEY=ollama
export OLLAMA_MODEL=qwen2.5:1.5b

# Start Ollama locally first:
# ollama pull qwen2.5:1.5b
# ollama run qwen2.5:1.5b

python -m src.agent
```

Then at the `You: ` prompt, ask natural-language questions like:
- "Show me all medical sector accounts with more than 500 employees"
- "Which deals did Moses Frase win over $1000?"
- "List all products in the GTX series and their prices"

The LLM will:
1. Parse your question
2. Call `query_crm_data` with appropriate table, conditions, and limit
3. Receive the JSON result
4. Compose a natural-language answer

### Schema for LLM Integration

The tool schema (sent to the LLM via `tools=[...]` in the API call) looks like:

```python
{
    "type": "function",
    "name": "query_crm_data",
    "description": "Query the CRM's tabular data...",
    "parameters": {
        "type": "object",
        "properties": {
            "table": {
                "type": "string",
                "enum": ["accounts", "products", "sales_pipeline", "sales_teams"],
                "description": "Which table to query."
            },
            "conditions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "operator": {
                            "type": "string",
                            "enum": ["eq", "ne", "contains", "gt", "gte", "lt", "lte"]
                        },
                        "value": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            "limit": {"type": "integer"}
        },
        "required": ["table"]
    }
}
```

The schema description includes a full listing of all tables and their columns/descriptions, dynamically generated from `datasets/metadata.csv`.

## Key Files

### `src/tools/metadata.py`

Loads and caches `datasets/metadata.csv` once per process:

```python
get_table_names() -> list[str]
get_columns(table: str) -> list[str]
get_column_description(table: str, column: str) -> str
validate_table(table: str) -> None  # raises ValueError
validate_column(table: str, column: str) -> None  # raises ValueError
```

### `src/tools/tools.py`

Core filtering logic:

```python
load_table(table: str) -> pd.DataFrame
filter_dataframe(table: str, conditions: list[dict] | None = None) -> pd.DataFrame
query_crm_data(table: str, conditions: list[dict] | None = None, limit: int = 50) -> dict
```

Returns a JSON-safe dict with:
- `table`: the queried table name
- `total_matches`: count of all matching rows
- `returned_count`: count of rows in the `rows` array
- `truncated`: boolean (true if truncated to `limit`)
- `limit_applied`: the effective limit (clamped to MAX_ROW_LIMIT=500)
- `rows`: array of matching rows as dicts

### `src/tools/schema.py`

```python
build_tool_schema() -> dict
```

Builds the OpenAI/Ollama-compatible function-calling schema. Called each turn by the agent loop; metadata is cached so it's fast.

### `src/agent.py`

Orchestrates the LLM interaction:

```python
get_client() -> OpenAI
call_tool(name: str, arguments: dict) -> dict
run_turn(client: OpenAI, model: str, user_input: str) -> str
main() -> None  # REPL loop
```

Flow:
1. Send user input + tool schema to the LLM
2. If LLM returns a `tool_use` block, extract and invoke the tool
3. Send tool result back to LLM for a final answer
4. Loop up to `MAX_TOOL_ITERATIONS=5` times per turn to handle chained tool calls

**Note**: Uses OpenAI SDK's `beta.messages.create` (Anthropic-compatible tool-calling format). This will work with Ollama's OpenAI-compatible endpoint; if the endpoint doesn't support this format, fall back to `client.chat.completions.create(..., tools=[...])` which is more widely supported by Ollama.

## Testing & Verification

All core logic is unit-testable without the LLM:

```bash
cd /Users/shrikantsavadatti/repos/tool-calling
python3 -c "
import sys
sys.path.insert(0, 'src')
from tools import query_crm_data

# Test multi-table queries, operators, error handling, truncation
result = query_crm_data(
    table='sales_pipeline',
    conditions=[
        {'column': 'deal_stage', 'operator': 'eq', 'value': ['Won']},
        {'column': 'close_value', 'operator': '>', 'value': ['1000']},
    ],
    limit=5
)
print(f'Found {result[\"total_matches\"]} deals, showing {result[\"returned_count\"]}')
"
```

Expected behaviors:
- ✓ All 4 tables load and filter independently
- ✓ Operators work: `eq`, `ne`, `contains`, numeric comparisons
- ✓ AND logic across conditions
- ✓ Multi-value `eq`/`ne`/`contains` (multiple values OR'd together)
- ✓ Single-value enforcement for numeric operators
- ✓ Error messages for unknown table/column/operator
- ✓ Row truncation at MAX_ROW_LIMIT=500
- ✓ JSON serialization of all results (numpy types handled correctly)

## Migration from Original

The old `get_accounts_data_by_filter()` and `get_accounts_metadata()` are removed entirely — they were only called by debug `print()` statements at the bottom of the old `tools.py`, which are also removed. No other code in the repo depends on them.

## What Changed from Original Implementation

1. **Generalized**: Supports all 4 tables, not just accounts
2. **Metadata-driven**: Column validation and descriptions from `datasets/metadata.csv`, keeping schema in sync
3. **Multi-condition filtering**: `conditions` is a list, not a single `column`/`operator`/`filter_value` triplet
4. **Cleaner operators**: Dropped confusing `in`/`not_in` aliasing
5. **Fixed numeric operator bug**: Multi-value now raises an error (as intended); ranges use two ANDed conditions
6. **Better error messages**: LLM-friendly, tells the model what went wrong and what values are valid
7. **Row limiting**: Hard capped at 500 rows to prevent context overflow
8. **Schema-driven LLM wiring**: Full dispatch loop, tool registry, and REPL entrypoint in `agent.py`
9. **No side effects on import**: Removed module-level `print()` calls from `tools.py`

## Future Enhancements

- Add support for `IN` (multi-value numeric range via a special syntax or as a pre-computed list)
- Add `between` operator as a convenience (translates to two ANDed `gt`/`lt` conditions)
- Add support for date range filters on `engage_date`/`close_date` in sales_pipeline
- Add a second tool `introspect_crm_schema()` to dynamically describe table structure if the model needs it during a conversation
- Support for joining across tables (e.g., "which medical-sector accounts have won deals over $1000?")
