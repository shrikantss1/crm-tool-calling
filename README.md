# Tool Calling

This project explores prompt engineering patterns and LLM tool-calling patterns using a local Ollama setup with the OpenAI-compatible client.

## Prerequisites

Before running the notebook, make sure Ollama is installed and the Qwen model is running locally.

Create a local `.env` file from `.env.example` and update the values if needed:

```bash
cp .env.example .env
```

Example `.env` values:

```env
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=ollama
OLLAMA_MODEL=qwen2.5:1.5b
```

Then start the model locally:

```bash
ollama pull qwen2.5:1.5b
ollama run qwen2.5:1.5b
```

The notebook expects the local Ollama server to be available at the base URL configured in `.env`.

## Notebook summary

The notebook in `modules/1_prompts/prompt_types.ipynb` demonstrates several prompting styles and how to evaluate them in a reusable way:

- One-shot prompting
- Zero-shot prompting
- Few-shot prompting
- Local Ollama model execution
- Token usage tracking
- Illustrative pricing estimation using a token-based pricing context

The examples are designed to help compare how different prompt structures affect model responses while keeping the request flow consistent.

## Project structure

- `modules/1_prompts/prompt_types.ipynb` – notebook with prompt examples and pricing demo
- `modules/pricing_context.py` – reusable pricing helper for token-based cost illustration
- `.env` – local environment values for Ollama connection

## Prompting technique comparison

### When to Use Each

| Technique | Best For | Example |
| --- | --- | --- |
| CoT | Quick decisions, simple reasoning | "What's the best time to launch?" |
| SC-CoT | Risk-sensitive decisions, consensus needed | "Should we hire this candidate?" |
| ToT | Complex problems, exploring options | "How should we restructure the team?" |

> The pricing logic is illustrative only. The notebook calls a local Ollama model, so the examples use hosted-model pricing for demonstration purposes, not actual billing for local inference.
