"""LangChain tool factory for fraud-check LLM agents."""


def build_tools(sync_db_uri: str) -> tuple:
    """Create SQL-only tools for LLM agent invocation.

    Only provides sql_db_query — no query_checker (extra LLM call),
    no analysis tools (agents compute scores directly from SQL results).
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    from app.agentic_system.tools.sql.toolkit import (
        create_sql_toolkit,
        get_query_tools,
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview", temperature=0.0,
    )
    toolkit = create_sql_toolkit(sync_db_uri, llm)
    return tuple(get_query_tools(toolkit))
