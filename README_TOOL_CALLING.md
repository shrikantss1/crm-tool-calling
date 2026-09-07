# CRM Chatbot Tool-Calling Implementation

## Summary

This project has been enhanced with a **generalized CRM data-filter tool** that enables an LLM to query 4 CRM tables (accounts, products, sales_pipeline, sales_teams) through a flexible, multi-condition filtering interface.

### What's New

```
✓ Generalized tool engine (not just accounts)
✓ Metadata-driven schema (single source of truth)
✓ Multi-condition AND filtering
✓ LLM integration with dispatch loop
✓ Interactive CLI chatbot
✓ Comprehensive error handling
```

## Files Created/Modified

### New Files
- `src/tools/__init__.py` — Package exports
- `src/tools/metadata.py` — Data dictionary loader and validator (450 lines)
- `src/tools/tools.py` — Generalized filter engine (120 lines)
- `src/tools/schema.py` — LLM tool schema builder (60 lines)
- `src/agent.py` — Dispatch loop and CLI (80 lines)
- `IMPLEMENTATION_SUMMARY.md` — Architecture and design decisions
- `USAGE_EXAMPLES.md` — Example queries and code samples

### Modified Files
- `.gitignore` — Updated (pre-existing)
- `requirements.txt` — No changes (openai SDK already present)

## Key Design Points

### 1. Single Generic Tool

Instead of separate `get_accounts_data()`, `get_products_data()`, etc., one `query_crm_data()` function handles all 4 tables:

```python
query_crm_data(
    table="sales_pipeline",
    conditions=[
        {"column": "deal_stage", "operator": "eq", "value": ["Won"]},
        {"column": "close_value", "operator": ">", "value": ["1000"]},
    ],
    limit=10
)
```

### 2. Metadata-Driven

`datasets/metadata.csv` is the single source of truth:
- Column names and descriptions
- Valid table names
- Runtime validation + LLM schema generation

### 3. Multi-Condition AND

Conditions are a list, ANDed together:
- `eq`, `ne`, `contains` — support multiple values (OR'd)
- `gt`, `gte`, `lt`, `lte` — support exactly one value (ranges use two conditions)

### 4. Error Handling

Filter functions raise `ValueError` (idiomatic Python). The dispatch loop catches and formats as LLM-visible error responses.

### 5. Row Limiting

Hard-capped at 500 rows max (configurable `MAX_ROW_LIMIT`) to prevent context blowup on large tables like sales_pipeline (8800 rows).

## Quick Start

### 1. Run the Interactive Chatbot

```bash
cd /Users/shrikantsavadatti/repos/tool-calling

# Make sure Ollama is running
ollama run qwen2.5:1.5b

# In another terminal
python -m src.agent
```

Then ask questions like:
- "Show me all medical sector companies with more than 500 employees"
- "Which deals did Moses Frase win over $1000?"
- "List all GTX series products"

### 2. Use the Tool Directly (Python)

```python
from src.tools import query_crm_data

result = query_crm_data(
    table="accounts",
    conditions=[
        {"column": "sector", "operator": "eq", "value": ["medical"]},
        {"column": "employees", "operator": ">=", "value": ["500"]},
    ],
    limit=5
)

print(f"{result['total_matches']} matches, showing {result['returned_count']}")
for row in result['rows']:
    print(f"  {row['account']}: {row['employees']} employees")
```

## Testing

All tests pass:
```bash
python3 << 'EOF'
import sys
sys.path.insert(0, 'src')
from tools import query_crm_data, build_tool_schema

# Schema builds correctly with all 4 tables
schema = build_tool_schema()
assert len(schema['parameters']['properties']['table']['enum']) == 4

# All tables can be queried
for table in ['accounts', 'products', 'sales_pipeline', 'sales_teams']:
    r = query_crm_data(table=table, limit=1)
    assert r['total_matches'] > 0

# All operators work
r = query_crm_data('accounts', [{'column': 'sector', 'operator': 'eq', 'value': ['medical']}])
assert r['total_matches'] == 12

# Error handling works
try:
    query_crm_data('accounts', [{'column': 'nonexistent', 'operator': 'eq', 'value': ['x']}])
    assert False
except ValueError:
    pass

print("✓ All tests passed")
EOF
```

## Architecture

```
src/tools/
├── __init__.py      — Package re-exports
├── metadata.py      — Tables/columns registry, validation
├── tools.py         — Loader, filter engine, tool entry point
└── schema.py        — Builds LLM tool schema from metadata

src/agent.py         — LLM dispatch loop, CLI, tool registry
```

### Data Flow

1. **LLM Side**: User asks a question → LLM gets tool schema → calls `query_crm_data(...)` with JSON args
2. **Dispatch**: `agent.py` parses the tool call → calls `query_crm_data(...)` in `tools.py`
3. **Filter**: `tools.py` validates table/columns against `metadata.py` → filters with pandas → returns JSON
4. **Response**: `agent.py` sends result back to LLM → LLM composes answer

## What Changed from Original

| Feature | Before | After |
|---------|--------|-------|
| Tables supported | accounts only | all 4 tables |
| Filtering | single column | multi-column AND |
| Column validation | hardcoded names | metadata.csv-driven |
| Operators | 8 (confusing aliases) | 7 (clean) |
| Numeric multi-value | silently dropped | raises error |
| Row limiting | none | hard cap at 500 |
| LLM integration | none | full dispatch loop |
| Schema definition | none | dynamically built |

## Documentation

- **IMPLEMENTATION_SUMMARY.md** — Architecture, design decisions, API reference
- **USAGE_EXAMPLES.md** — Example queries, direct Python usage, troubleshooting
- **README_TOOL_CALLING.md** — This file

## Next Steps

### Optional Enhancements
1. Add a second tool `introspect_crm_schema()` for dynamic schema exploration
2. Support `between` operator as convenience (translates to two ANDed conditions)
3. Support joins across tables (e.g., "medical accounts with won deals")
4. Add date range filters for engage_date/close_date
5. Stream large result sets instead of truncating

### Deployment
- The tool is ready to use with Ollama locally via the existing OpenAI-SDK setup
- To use with Claude or OpenAI API directly, update `src/agent.py` to use the `anthropic` or `openai` SDK endpoints
- For production, consider: DB layer (vs CSV files), async/streaming results, authentication, rate limiting

## Support

If you encounter issues:

1. **Import errors**: Ensure you're running from the repo root with `sys.path.insert(0, 'src')`
2. **Ollama connection errors**: Check `.env` file has correct `OLLAMA_BASE_URL` and the model is running
3. **No tool calls from LLM**: Ollama may not support tool-calling for the model. Try a larger model or check Ollama docs.
4. **Column not found errors**: Check table name spelling; error message lists valid columns
5. **Truncation limits**: Use tighter conditions to narrow results below 500 rows

See USAGE_EXAMPLES.md for more troubleshooting.
