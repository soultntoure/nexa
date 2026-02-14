"""Reusable BaseAgent wrapping LangChain 1.0 create_agent with Google Gemini."""

import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware.types import AgentMiddleware
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from app.agentic_system.tools.sql.read_only_middleware import read_only_sql

load_dotenv()

logger = logging.getLogger(__name__)



@dataclass(frozen=True)
class AgentConfig:
    """Immutable configuration for a BaseAgent instance.

    api_key is read from env GOOGLE_API_KEY by ChatGoogleGenerativeAI.
    """

    prompt: str
    model: str = "gemini-3-flash-preview"
    temperature: float = 0.0
    tools: tuple[BaseTool, ...] = ()
    middleware: tuple[AgentMiddleware, ...] = ()
    output_schema: type[BaseModel] | None = None
    thinking_budget: int | None = None
    thinking_level: str | None = None
    max_tokens: int | None = None
    timeout: float | None = None
    max_retries: int = 2
    max_iterations: int | None = None


class BaseAgent:
    """Thin wrapper around LangChain 1.0 create_agent.

    Supports plain text, structured output, tool-calling, and streaming.
    Designed for composition — other agents own a BaseAgent, not subclass it.
    """

    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._llm = self._build_llm()
        self._agent = self._build_agent()

    def _build_llm(self) -> ChatGoogleGenerativeAI:
        kwargs: dict[str, Any] = {
            "model": self._config.model,
            "temperature": self._config.temperature,
            "max_retries": self._config.max_retries,
        }
        if self._config.max_tokens is not None:
            kwargs["max_tokens"] = self._config.max_tokens
        if self._config.timeout is not None:
            kwargs["timeout"] = self._config.timeout
        if self._config.thinking_budget is not None:
            kwargs["thinking_budget"] = self._config.thinking_budget
        if self._config.thinking_level is not None:
            kwargs["thinking_level"] = self._config.thinking_level
        return ChatGoogleGenerativeAI(**kwargs)

    def _build_agent(self) -> Any:
        """Build agent via create_agent. Handles all config combos."""
        kwargs: dict[str, Any] = {
            "tools": list(self._config.tools),
            "system_prompt": self._config.prompt,
        }
        if self._config.output_schema:
            kwargs["response_format"] = self._config.output_schema

        middleware = list(self._config.middleware)
        if self._has_sql_tools() and read_only_sql not in middleware:
            middleware.insert(0, read_only_sql)
        if middleware:
            kwargs["middleware"] = middleware

        return create_agent(self._llm, **kwargs)

    def _has_sql_tools(self) -> bool:
        """Check if any tool is the sql_db_query tool."""
        return any(
            getattr(t, "name", "") == "sql_db_query"
            for t in self._config.tools
        )

    def _invoke_config(self) -> dict[str, Any]:
        """Build config dict with recursion_limit if max_iterations is set."""
        if self._config.max_iterations is not None:
            return {"recursion_limit": self._config.max_iterations * 2 + 1}
        return {}

    async def invoke(self, user_input: str) -> BaseModel | str:
        """One-shot async execution. Returns structured output or string."""

        result = await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=self._invoke_config(),
        )
        return self._extract_output(result)

    async def invoke_verbose(self, user_input: str) -> tuple[BaseModel | str, list[dict[str, Any]]]:
        """Like invoke but also returns a trace of tool calls."""

        result = await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=self._invoke_config(),
        )
        trace = _extract_tool_trace(result.get("messages", []))
        return self._extract_output(result), trace

    async def stream(self, user_input: str) -> AsyncGenerator[str, None]:
        """Stream tokens from the agent response."""

        async for token, _metadata in self._agent.astream(
            {"messages": [{"role": "user", "content": user_input}]},
            stream_mode="messages",
        ):
            if token.content:
                yield token.content

    def _extract_output(self, result: dict[str, Any]) -> BaseModel | str:
        """Pull structured response or last message content."""
        if self._config.output_schema and "structured_response" in result:
            return result["structured_response"]
        messages = result.get("messages", [])
        return messages[-1].content if messages else ""


def _extract_tool_trace(messages: list[Any]) -> list[dict[str, Any]]:
    """Build tool trace pairing each tool call with its result."""
    pending: dict[str, dict[str, Any]] = {}
    trace: list[dict[str, Any]] = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                entry = {
                    "tool": tc.get("name", "?"),
                    "args_preview": str(tc.get("args", ""))[:200],
                    "result_preview": "",
                }
                call_id = tc.get("id", "")
                if call_id:
                    pending[call_id] = entry
                trace.append(entry)
        if hasattr(msg, "tool_call_id") and msg.tool_call_id:
            entry = pending.get(msg.tool_call_id)
            if entry:
                entry["result_preview"] = str(getattr(msg, "content", ""))[:200]
    return trace
