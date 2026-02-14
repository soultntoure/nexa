"""SQLDatabaseToolkit setup — LangChain SQL Agent pattern.

Provides 4 built-in tools via toolkit.get_tools():
  - sql_db_list_tables
  - sql_db_schema
  - sql_db_query (read-only)
  - sql_db_query_checker (LLM validation)
"""

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool

FRAUD_DB_TABLES: list[str] = [
    "customers",
    "withdrawals",
    "transactions",
    "trades",
    "payment_methods",
    "devices",
    "ip_history",
    "withdrawal_decisions",
    "indicator_results",
    "alerts",
    "threshold_config",
]


def create_sql_toolkit(
    db_uri: str, llm: BaseLanguageModel
) -> SQLDatabaseToolkit:
    """Create a SQLDatabaseToolkit from a database URI and LLM."""
    db = SQLDatabase.from_uri(
        db_uri,
        include_tables=FRAUD_DB_TABLES,
        sample_rows_in_table_info=0,
    )
    return SQLDatabaseToolkit(db=db, llm=llm)


def get_sql_tools(toolkit: SQLDatabaseToolkit) -> list[BaseTool]:
    """Extract the 4 built-in SQL tools from a toolkit."""
    return toolkit.get_tools()


# Tools to skip: schema already in prompt, query_checker adds an extra LLM round-trip
_SKIP_TOOLS = {"sql_db_list_tables", "sql_db_schema", "sql_db_query_checker"}


def get_query_tools(toolkit: SQLDatabaseToolkit) -> list[BaseTool]:
    """Only sql_db_query — skip schema/list/checker to minimize LLM round-trips."""
    return [t for t in toolkit.get_tools() if t.name not in _SKIP_TOOLS]
