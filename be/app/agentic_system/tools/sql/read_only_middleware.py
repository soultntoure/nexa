"""Read-only SQL middleware — blocks mutating queries before tool execution.

Subclasses LangChain's AgentMiddleware to intercept sql_db_query calls and
reject any query containing INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE,
CREATE, GRANT, REVOKE, or EXEC statements.

Usage:
    from langchain.agents import create_agent
    from app.agentic_system.tools.sql.read_only_middleware import read_only_sql

    agent = create_agent(model, tools=tools, middleware=[read_only_sql])
"""

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

logger = logging.getLogger(__name__)

_SQL_TOOL_NAME = "sql_db_query"

_MUTATING_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC)\b",
    re.IGNORECASE,
)


class ReadOnlySQLViolation(Exception):
    """Raised when a mutating SQL statement is detected."""

    def __init__(self, query: str, keyword: str) -> None:
        self.query = query
        self.keyword = keyword
        super().__init__(f"Blocked mutating SQL keyword '{keyword}' in query")


def detect_mutating_sql(query: str) -> str | None:
    """Return the first mutating keyword found in *query*, or None if clean."""
    match = _MUTATING_PATTERN.search(query)
    return match.group(1).upper() if match else None


class ReadOnlySQLMiddleware(AgentMiddleware):  # type: ignore[type-arg]
    """Intercepts sql_db_query tool calls and blocks mutating statements."""

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """Block mutating SQL before execution, pass SELECT queries through."""
        tool_name = request.tool_call.get("name", "")

        if tool_name != _SQL_TOOL_NAME:
            return await handler(request)

        query = request.tool_call.get("args", {}).get("query", "")
        keyword = detect_mutating_sql(query)

        if keyword is not None:
            logger.warning(
                "ReadOnlySQLMiddleware blocked mutating query: keyword=%s query=%.200s",
                keyword,
                query,
            )
            return ToolMessage(
                content=(
                    f"BLOCKED: Mutating SQL statement '{keyword}' is not allowed. "
                    "This system is read-only. Only SELECT queries are permitted."
                ),
                tool_call_id=request.tool_call.get("id", ""),
                status="error",
            )

        return await handler(request)


# Singleton instance — use this in middleware lists
read_only_sql = ReadOnlySQLMiddleware()
