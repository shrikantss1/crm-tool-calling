import os
import sqlite3
from functools import lru_cache

import pandas as pd
from dotenv import load_dotenv
from langchain_community.agent_toolkits import SQLDatabaseToolkit, create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI

from tools.metadata import METADATA_CSV_PATH, TABLE_PATHS


@lru_cache(maxsize=1)
def get_agent():
    load_dotenv()

    accounts_df = pd.read_csv(TABLE_PATHS["accounts"])
    metadata_df = pd.read_csv(METADATA_CSV_PATH)
    products_df = pd.read_csv(TABLE_PATHS["products"])
    sales_pipeline_df = pd.read_csv(TABLE_PATHS["sales_pipeline"])
    sales_teams = pd.read_csv(TABLE_PATHS["sales_teams"])

    llm = ChatOpenAI(model="gpt-4", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    # llm = ChatOpenAI(
    #     model= os.getenv("OLLAMA_MODEL"), 
    #     base_url=os.getenv("OLLAMA_BASE_URL"), 
    #     api_key=os.getenv("OLLAMA_API_KEY"), 
    #     temperature=0,
    #     extra_body={"options": {"thinking": False}} )

    conn = sqlite3.connect("crm-database.db")
    accounts_df.to_sql("accounts", conn, if_exists="replace", index=False)
    metadata_df.to_sql("metadata", conn, if_exists="replace", index=False)
    products_df.to_sql("products", conn, if_exists="replace", index=False)
    sales_pipeline_df.to_sql("sales_pipeline", conn, if_exists="replace", index=False)
    sales_teams.to_sql("sales_teams", conn, if_exists="replace", index=False)
    conn.close()

    db = SQLDatabase.from_uri("sqlite:///crm-database.db")

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return create_sql_agent(
        llm=llm,
        # db=db,
        toolkit=toolkit,
        agent_type="openai-tools",
        verbose=True,
    )


if __name__ == "__main__":
    agent = get_agent()
    messages = [{"role": "system", "content": "You are a helpful CRM assistant. "}]
    while True:
        query = input("[You] Enter your  query: ")
        if query.lower() in ["exit", "quit"]:
            break
        messages.append({"role": "user", "content": query})
        response = agent.invoke({"input": messages})
        messages.append({"role": "assistant", "content": response['output']})
        print(f"[Bot]: {response}")



