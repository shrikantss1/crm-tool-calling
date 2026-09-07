import json
import logging
import os
from typing import Callable

from dotenv import load_dotenv
from openai import OpenAI

from tools import build_tool_schema, query_crm_data

TOOL_REGISTRY: dict[str, Callable[..., dict]] = {"query_crm_data": query_crm_data}
MAX_TOOL_ITERATIONS = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def get_client(provider: str = "ollama") -> tuple[OpenAI, str]:
    load_dotenv(override=True)
    logger.debug("Initializing OpenAI client")
    if provider == "openai":
        client =  OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        model = os.getenv("OPENAI_MODEL")
        return client, model
    else:
        client = OpenAI(
            base_url=os.getenv("OLLAMA_BASE_URL"),
            api_key=os.getenv("OLLAMA_API_KEY"),
        )
        model = os.getenv("OLLAMA_MODEL")
        return client, model



def call_tool(name: str, arguments: dict) -> dict:
    if name not in TOOL_REGISTRY:
        logger.debug("Unknown tool requested: %s", name)
        return {"error": f"Unknown tool '{name}'"}

    logger.info("Calling tool '%s' with arguments=%s", name, arguments)
    try:
        result = TOOL_REGISTRY[name](**arguments)
        logger.debug("Tool '%s' succeeded: %s", name, result)
        return result
    except Exception as exc:
        error_result = {"error": str(exc), "error_type": type(exc).__name__}
        logger.exception("Tool '%s' raised an exception: %s", name, error_result)
        return error_result


def run_turn(client: OpenAI, model: str, user_input: str) -> str:
    logger.debug("Starting run_turn for input=%r", user_input)
    tools_param = [build_tool_schema()]
    response = client.responses.create(
        model=model,
        tools=tools_param,
        input=[{"role": "user", "content": user_input}],
    )
    logger.debug("Initial model response received: %s", response)

    for iteration in range(MAX_TOOL_ITERATIONS):
        tool_calls = [
            block
            for block in response.output
            if getattr(block, "type", None) in {"tool_use", "function_call"}
        ]
        if not tool_calls:
            logger.debug("No tool calls found on iteration %d; stopping", iteration + 1)
            break

        logger.info("Iteration %d: processing %d tool call(s)", iteration + 1, len(tool_calls))

        messages = [{"role": "user", "content": user_input}]

        for tool_call in tool_calls:
            tool_name = getattr(tool_call, "name", None)
            tool_input = getattr(tool_call, "input", None)
            if tool_input is None:
                tool_input = json.loads(getattr(tool_call, "arguments", "{}") or "{}")

            logger.debug("Executing tool '%s' with input=%s", tool_name, tool_input)
            result = call_tool(tool_name, tool_input)

            messages.append({
                "type": "function_call",
                "call_id": getattr(tool_call, "call_id", getattr(tool_call, "id", None)),
                "name": tool_name,
                "arguments": json.dumps(tool_input),
            })
            messages.append({
                "type": "function_call_output",
                "call_id": getattr(tool_call, "call_id", getattr(tool_call, "id", None)),
                "output": json.dumps(result),
            })

        logger.debug("Sending %d tool result(s) back to model", len(tool_calls))

        response = client.responses.create(
            model=model,
            tools=tools_param,
            input=messages,
        )
        logger.debug("Follow-up model response received: %s", response)

    for block in response.output:
        if getattr(block, "type", None) == "message":
            for content in getattr(block, "content", []):
                if getattr(content, "type", None) == "output_text":
                    logger.debug("Returning assistant text from response.output")
                    return content.text

    logger.debug("No assistant text found in final response output")
    return ""


def main() -> None:
    client, model = get_client("openai")
    logger.debug("Using model=%s", model)

    print("CRM Chatbot (type 'exit' or 'quit' to quit)")
    print("-" * 50)

    while True:
        user_input = input("You: ").strip()
        # user_input = "Acme Corporation"
        logger.debug("Received user input: %r", user_input)

        if user_input.lower() in {"exit", "quit"}:
            logger.debug("User requested exit")
            break
        if not user_input:
            logger.debug("Empty input ignored")
            break

        try:
            response = run_turn(client, model, user_input)
            print(f"Bot: {response}\n")
            logger.debug("Bot response printed")
            # raise SystemExit
        except Exception as exc:
            logger.exception("Unhandled exception while processing request")
            print(f"Error: {exc}\n", exc)
            # raise SystemExit


if __name__ == "__main__":
    main()
