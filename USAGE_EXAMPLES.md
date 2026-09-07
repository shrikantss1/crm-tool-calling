# CRM Chatbot Tool Usage Examples

## Quick Start

### Setup
```bash
cd /Users/shrikantsavadatti/repos/tool-calling

# Make sure Ollama is running
ollama pull qwen2.5:1.5b  # First time only
ollama run qwen2.5:1.5b   # Start the model

# In another terminal, run the chatbot
python -m src.agent
```

### Example Conversations

#### Example 1: Simple Filter
```
You: Show me all medical sector companies

Bot: I'll search for companies in the medical sector.
[Tool call: query_crm_data(table="accounts", conditions=[{"column":"sector","operator":"eq","value":["medical"]}])]

Bot: I found 12 companies in the medical sector. Here are the first few:
- Betasoloin (United States, 495 employees, founded 1999)
- Betatech (Kenya, 1185 employees, founded 1986)
- Bioholding (Philippines, 1356 employees, founded 2012)
... and 9 more.
```

#### Example 2: Multiple Conditions
```
You: Which deals did Moses Frase win over $1000?

Bot: Let me find deals for Moses Frase with value over $1000.
[Tool call: query_crm_data(table="sales_pipeline", conditions=[
  {"column":"sales_agent","operator":"eq","value":["Moses Frase"]},
  {"column":"deal_stage","operator":"eq","value":["Won"]},
  {"column":"close_value","operator":">","value":["1000"]}
])]

Bot: Moses Frase won 2 deals over $1000:
1. Opportunity 1C1I7A6R: GTX Plus Basic at Cancity ($1054)
2. Opportunity MV1LWRNH: GTX Basic at Codehow ($1200)
```

#### Example 3: Substring Search
```
You: Find all office locations in the United States

Bot: Looking for US offices...
[Tool call: query_crm_data(table="accounts", conditions=[
  {"column":"office_location","operator":"contains","value":["United States"]}
])]

Bot: Found 45 companies with offices in the United States.
```

#### Example 4: Numeric Range (via two AND conditions)
```
You: Show me mid-sized companies with 500 to 1500 employees

Bot: Let me find companies in that employee range.
[Tool call: query_crm_data(table="accounts", conditions=[
  {"column":"employees","operator":">=","value":["500"]},
  {"column":"employees","operator":"<=","value":["1500"]}
], limit=10)]

Bot: Found 23 mid-sized companies (showing first 10):
- Betasoloin (495 employees) - close!
- Betatech (1185 employees)
- Bioholding (1356 employees)
... and 7 more.
```

## Direct Python Usage (No LLM)

### Single Table Query
```python
from src.tools import query_crm_data

result = query_crm_data(
    table="products",
    limit=5
)

print(f"Products: {len(result['rows'])} of {result['total_matches']}")
for product in result['rows']:
    print(f"  - {product['product']}: ${product['sales_price']}")
```

Output:
```
Products: 5 of 7
  - GTX Basic: $550
  - GTX Pro: $4821
  - MG Special: $55
  - MG Advanced: $3393
  - MG Plus Basic: $1075
```

### Complex Filtering
```python
from src.tools import query_crm_data

# Find all "Won" deals from the GTX product line over $2000
result = query_crm_data(
    table="sales_pipeline",
    conditions=[
        {"column": "deal_stage", "operator": "eq", "value": ["Won"]},
        {"column": "product", "operator": "contains", "value": ["GTX"]},
        {"column": "close_value", "operator": ">", "value": ["2000"]},
    ],
    limit=5
)

print(f"Found {result['total_matches']} matching deals")
for deal in result['rows']:
    print(f"  {deal['opportunity_id']}: {deal['product']} - ${deal['close_value']}")

if result['truncated']:
    print(f"  ... and {result['total_matches'] - result['returned_count']} more")
```

Output:
```
Found 118 matching deals
  Z063OYW0: GTXPro - $4514
  OLK9LKZB: GTX Plus Basic - $1026
  PQ2MLZOP: GTX Pro - $2847
  RS3NBAQP: GTX Plus Basic - $2100
  TU4OCRQS: GTX Basic - $3456
  ... and 113 more
```

### Error Handling
```python
from src.tools import query_crm_data

try:
    # Query with invalid column
    result = query_crm_data(
        table="accounts",
        conditions=[{"column": "invalid_column", "operator": "eq", "value": ["test"]}]
    )
except ValueError as e:
    print(f"Error: {e}")
    # Output: Error: Column 'invalid_column' not found in table 'accounts'. 
    #         Valid columns: account, sector, year_established, revenue, employees, 
    #                        office_location, subsidiary_of
```

## Schema Information

### Available Tables

1. **accounts** (85 rows)
   - Columns: account, sector, year_established, revenue, employees, office_location, subsidiary_of
   - Sample query: Find all tech companies with >1000 employees

2. **products** (7 rows)
   - Columns: product, series, sales_price
   - Sample query: List all products in the GTX series

3. **sales_pipeline** (8800 rows)
   - Columns: opportunity_id, sales_agent, product, account, deal_stage, engage_date, close_date, close_value
   - Sample query: Find won deals over $1000 closed in 2017

4. **sales_teams** (35 rows)
   - Columns: sales_agent, manager, regional_office
   - Sample query: Find all agents managed by a specific person

### Operators

| Operator | Aliases | Example Use |
|----------|---------|------------|
| `eq` | `==`, `equals` | Find accounts where sector == "medical" |
| `ne` | `!=`, `not_equals` | Find deals where stage != "Lost" |
| `contains` | `like`, `includes` | Find locations containing "United" |
| `gt` | `>` | Find companies with employees > 1000 |
| `gte` | `>=` | Find deals with close_value >= 5000 |
| `lt` | `<` | Find products with price < 1000 |
| `lte` | `<=` | Find accounts established <= 2000 |

### Result Structure

Every query returns a JSON object:
```json
{
  "table": "accounts",
  "total_matches": 45,
  "returned_count": 10,
  "truncated": true,
  "limit_applied": 10,
  "rows": [
    {
      "account": "Acme Corporation",
      "sector": "technology",
      "year_established": 1996,
      "revenue": 1100.04,
      "employees": 2822,
      "office_location": "United States",
      "subsidiary_of": null
    },
    ...
  ]
}
```

- `total_matches`: Total number of rows matching the conditions (before truncation)
- `returned_count`: Actual rows in the `rows` array
- `truncated`: True if total_matches > returned_count
- `limit_applied`: The effective limit used (capped at 500)
- `rows`: Array of matching records

## Tips for the LLM

1. **Always use conditions to filter**: Rather than asking "show me all deals", use conditions to narrow down: `conditions=[{"column":"deal_stage","operator":"eq","value":["Won"]}]`

2. **Use multiple conditions for complex queries**: The LLM will naturally combine "Find medical sector companies with >500 employees" into two ANDed conditions.

3. **For ranges, use two conditions**: "employees between 500-1500" becomes:
   - `{"column":"employees","operator":">=","value":["500"]}`
   - `{"column":"employees","operator":"<=","value":["1500"]}`

4. **Substring matching for flexibility**: "offices in the US" can use `contains` with "United" to match variations.

5. **Check the `truncated` flag**: If results are truncated, encourage the user to refine their query with tighter conditions.

## Troubleshooting

### "Unknown tool 'query_crm_data'"
The LLM tried to call a tool that isn't registered. Make sure `src/agent.py` is running and the tool registry includes `query_crm_data`.

### "Column 'X' not found"
The column name might be spelled differently. The error message will list valid columns for the table.

### "Operator 'X' requires exactly one value"
Numeric operators (`>`, `>=`, `<`, `<=`) only accept a single threshold. For ranges, use two ANDed conditions.

### No results returned
The conditions are too restrictive. Try loosening them or asking for all rows with `limit=100` to see what data exists.

### "Model appears to not support tool use"
The Ollama endpoint might not support tool-calling for the model you're using. Try upgrading to a larger model or check the Ollama tool-calling documentation.
