import json

import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()

TABLE_PATHS: dict[str, str] = {
    "continents": "datasets/continents.csv",
}

_continents_data = None
client = OpenAI()

MAX_ITERARIONS = 5
def load_continents_data() -> list[dict[str, str]]:
    global _continents_data
    if _continents_data is None:
        import csv

        with open(TABLE_PATHS["continents"], newline="") as csvfile:
            
            _continents_data = pd.read_csv(csvfile).to_dict(orient="records")
    return _continents_data


def get_continents_data(continent: str) -> list[dict[str, str]]:
    data = load_continents_data()
    if not continent:
        return []
    return [row for row in data if row.get("continent") == continent]

def get_ontinents_tools_schema() -> str:
    tools = [
        {
        "type": "function",
        "name": "get_continents_data",
        "description": "Get data for a specific continent",
        "parameters": {
                "type": "object",
                "properties": {
                    "continent": {
                        "type": "string",
                        "description": "The name of the continent"
                    }
                }
            },
        "required": ["continent"]
            
        }
    ]
    
    return tools

TOOL_NAMES = {
    "get_continents_data": get_continents_data
}

def run_continents_agent(user_input: str):
    
    messages = [
        {
            "role": "user",
            "content": user_input
        },
        {
            "role": "system",
            "content": "You are a helpful assistant that provides data about continents. "
            "Respond with accurate and concise information."
            "Respond only with data from the tool call. Nothing else"
            "Respond with proper user firendly message rather than JSON"
            "If no continent is specified, return an empty list."
            "If not countries are found, return appropriate message."
            "When max tool calls are reached, stop calling the tools and respond with whatever info you have."
        }
    ]

    tool_call_count = 0


    tools = get_ontinents_tools_schema()

    for iteration in range(MAX_ITERARIONS):
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL"),
            input=messages,
            tools=tools
        )
    
        for output in response.output:
            if output.type == "function_call":
                print(f"Function call detected: {output.name} , {output.arguments}")
                tool_call = TOOL_NAMES.get(output.name)
                if tool_call:
                        
                    arguments = eval(output.arguments)
                    print(f"Tool call arguments: {arguments}")
                    print(f"Total tool calls in this iteration: {tool_call_count}")

                    if tool_call_count >= 3:
                        print("Maximum tool call limit reached for this iteration.")
                        messages.append({
                                        "type": "function_call",
                                        "call_id": getattr(output, "call_id", getattr(output, "id", None)),
                                        "name": output.name,
                                        "arguments": json.dumps(output.arguments)
                                        })
                        messages.append({
                                        "type": "function_call_output",
                                        "call_id": getattr(output, "call_id", getattr(output, "id", None)),
                                        "name": output.name,
                                        "output": json.dumps({"error": "Maximum tool call limit reached"})
                                        })
                    else:
                        print("Calling tool with arguments...")
                        result = tool_call(**arguments)
                        messages.append({
                            "type": "function_call",
                            "call_id": getattr(output, "call_id", getattr(output, "id", None)),
                            "name": output.name,
                            "arguments": json.dumps(output.arguments)

                        })
                        messages.append({
                            "type": "function_call_output",
                            "call_id": getattr(output, "call_id", getattr(output, "id", None)),
                            "name": output.name,
                            "output": json.dumps(result)
                        })
                        tool_call_count += 1
                else:
                    print(f"No tool found for function call: {output.name}")
                    messages.append({
                        "role": "assistant",
                        "content": f"No tool found for function call: {output.name}"
                    })
            elif output.type == "reasoning":
                messages.append({
                    "role": "assistant",
                    "content": f"Reasoning: {output.encrypted_content}"
                })
            
            elif output.type == "message":
                # print(f"Message received: {output.content[0].text}")
                return output.content[0].text
            else:
                print(f"Unhandled output type: {output.type}")
                return "Invalid output type"
    return None 
    


if __name__ == "__main__":
    while True:
        user_input = input("You: Enter a continent to get data (or 'exit' to quit): ")
        if user_input.lower() == "exit":
            break
        result = run_continents_agent(user_input)
        print(f"Bot: {result}")