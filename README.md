# CRM Tool-Calling Demo

This project demonstrates tool calling with an OpenAI-compatible client against a small CRM dataset. The app exposes a single generic tool, `query_crm_data`, and lets an LLM decide which CRM table to query and which filters to apply before answering user questions.

It is designed to work with either:

- a local Ollama model, or
- a hosted OpenAI-compatible model

The project uses CSV-backed CRM data in the `datasets/` folder and a command-line chatbot in `src/agent.py`.

## What it does

The app can answer questions such as:

- "What is the account with name Acme Corporation?"
- "Which deals were won over $1000?"
- "List all products in the GTX series."
- "Show sales agents in the West region."

The LLM selects a CRM table and submits structured filter conditions such as:

```python
{
  "table": "accounts",
  "conditions": [
    {"column": "account", "operator": "eq", "value": ["Acme Corporation"]}
  ],
  "limit": 10
}
```

## Supported CRM tables

- `accounts`
- `products`
- `sales_pipeline`
- `sales_teams`

## Project structure

- `src/agent.py` — CLI chatbot and tool-calling loop
- `src/tools/schema.py` — tool schema definition for the LLM
- `src/tools/tools.py` — CRM query execution and filtering logic
- `src/tools/metadata.py` — dataset metadata and validation rules
- `datasets/` — sample CRM CSV files
- `README_TOOL_CALLING.md` — lower-level notes and usage examples
- `IMPLEMENTATION_SUMMARY.md` — project background and architecture notes

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Configure environment variables in a `.env` file:

```env
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=ollama
OLLAMA_MODEL=qwen2.5:1.5b

# optional for hosted OpenAI-compatible usage
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

4. Start your local model if using Ollama:

```bash
ollama pull qwen2.5:1.5b
ollama run qwen2.5:1.5b
```

## Run the chatbot

From the project root:

```bash
python src/agent.py
```

Then ask a question in the terminal. Type `exit` or `quit` to end the session.

## Tool behavior

The tool `query_crm_data` accepts:

- `table`: the CRM table to query
- `conditions`: a list of ANDed filters
- `limit`: maximum rows returned

Supported operators:

- `eq`
- `ne`
- `contains`
- `gt`
- `gte`
- `lt`
- `lte`

## Example queries

```python
from src.tools import query_crm_data

result = query_crm_data(
    table="accounts",
    conditions=[
        {"column": "account", "operator": "eq", "value": ["Acme Corporation"]}
    ],
    limit=10,
)

print(result)
```

```python
result = query_crm_data(
    table="sales_pipeline",
    conditions=[
        {"column": "deal_stage", "operator": "eq", "value": ["Won"]},
        {"column": "close_value", "operator": "gte", "value": ["1000"]},
    ],
    limit=20,
)
```

## Notes

- This is a demo project for learning tool calling with LLMs.
- Data is read from local CSV files, not a production database.
- The tool layer validates columns and table names before querying.
- Row results are capped to avoid large context windows.

## Related docs

- [README_TOOL_CALLING.md](README_TOOL_CALLING.md)
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
