"""Analyst chat service — streams fraud query answers via SSE events.

Uses LangChain create_agent with InMemorySaver checkpointer for
server-side conversation history. The client only sends a question
and a session_id — no history is sent from the frontend.

See docs/features/chat/01_streaming_flow.md for full client-to-API flow documentation.
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import create_engine

from app.agentic_system.prompts.analyst_chat import ANALYST_CHAT_PROMPT
from app.agentic_system.tools.sql.schema_builder import (
    build_critical_notes,
    build_schema_description,
)
from app.agentic_system.tools.sql.read_only_middleware import read_only_sql
from app.agentic_system.tools.sql.toolkit import (
    FRAUD_DB_TABLES,
    create_sql_toolkit,
    get_query_tools,
)
from app.agentic_system.tools.chart_tool import render_chart
from app.config import get_settings

logger = logging.getLogger(__name__)

# Module-level singleton
_agent: Any = None


def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


def _extract_text(content: str | list) -> str:
    """Extract plain text from Gemini content (str or list of parts)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            p.get("text", "") for p in content if isinstance(p, dict)
        )
    return str(content)


def init_analyst_agent() -> Any:
    """Build the analyst agent with InMemorySaver. Call once at startup."""
    global _agent
    settings = get_settings()
    sync_uri = settings.POSTGRES_URL.replace("+asyncpg", "").split("?")[0]

    sync_engine = create_engine(sync_uri)
    schema_docs = (
        build_schema_description(sync_engine, FRAUD_DB_TABLES)
        + build_critical_notes()
    )
    logger.info("Generated schema docs: %d chars", len(schema_docs))

    from langchain.agents import create_agent
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview", temperature=0.0, thinking_level="low",
    )
    toolkit = create_sql_toolkit(sync_uri, llm)
    sql_tools = get_query_tools(toolkit)
    all_tools = sql_tools + [render_chart]

    full_prompt = ANALYST_CHAT_PROMPT.replace(
        "## Database Schema (exact columns)", schema_docs
    )

    checkpointer = InMemorySaver()
    _agent = create_agent(
        llm,
        tools=all_tools,
        system_prompt=full_prompt,
        checkpointer=checkpointer,
        middleware=[read_only_sql],
    )
    logger.info("Analyst chat agent initialized with server-side memory")
    return _agent


async def warmup_analyst_agent() -> None:
    """Fire a cheap query to warm up LLM connection + SQL pool."""
    if _agent is None:
        init_analyst_agent()
    result = await _agent.ainvoke(
        {"messages": [{"role": "user", "content": "How many customers?"}]},
        config={"configurable": {"thread_id": "__warmup__"}},
    )
    msgs = result.get("messages", [])
    logger.info("Analyst chat warmup done (%d messages)", len(msgs))


async def stream_analyst_answer(
    question: str,
    session_id: str = "default",
) -> AsyncGenerator[str, None]:
    """Stream SSE events. History is managed server-side via thread_id."""
    global _agent
    if _agent is None:
        init_analyst_agent()

    yield _sse({"type": "status", "message": "Thinking..."})

    thread_config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": 25,
    }
    answer_parts: list[str] = []

    try:
        tools_used: set[str] = set()
        current_run_id: str | None = None
        current_run_parts: list[str] = []

        async for event in _agent.astream_events(
            {"messages": [{"role": "user", "content": question}]},
            version="v2",
            config=thread_config,
        ):
            kind = event.get("event", "")

            if kind == "on_tool_start":
                name = event.get("name", "unknown")
                tool_input = event.get("data", {}).get("input", {})
                query = str(tool_input.get("query", ""))[:500]
                if name == "sql_db_query":
                    tools_used.add(name)
                    yield _sse({
                        "type": "tool_start",
                        "name": name,
                        "preview": query,
                    })

            elif kind == "on_tool_end":
                name = event.get("name", "unknown")
                if name == "render_chart":
                    raw_output = event.get("data", {}).get("output", "")
                    output = getattr(raw_output, "content", str(raw_output))
                    try:
                        parsed = json.loads(output)
                        if parsed.get("__chart__"):
                            parsed.pop("__chart__")
                            yield _sse({
                                "type": "chart",
                                "chart": parsed,
                            })
                    except (json.JSONDecodeError, AttributeError):
                        logger.warning("event=render_chart_parse_error output=%s", output[:200])

                elif name == "sql_db_query":
                    output = str(
                        event.get("data", {}).get("output", "")
                    )[:2000]
                    yield _sse({
                        "type": "tool_end",
                        "name": name,
                        "result": output,
                    })

            elif kind == "on_chat_model_start":
                run_id = event.get("run_id", "")
                if run_id != current_run_id:
                    current_run_id = run_id
                    current_run_parts = []

            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    text = _extract_text(chunk.content)
                    if text:
                        current_run_parts.append(text)
                        yield _sse({"type": "token", "content": text})

            elif kind == "on_chat_model_end":
                output = event.get("data", {}).get("output")
                has_tool_calls = (
                    output
                    and hasattr(output, "tool_calls")
                    and output.tool_calls
                )
                if not has_tool_calls and current_run_parts:
                    answer_parts.extend(current_run_parts)
                elif not has_tool_calls and output and hasattr(output, "content"):
                    fallback_text = _extract_text(output.content)
                    if fallback_text:
                        answer_parts.append(fallback_text)
                        yield _sse({"type": "token", "content": fallback_text})
                elif has_tool_calls and current_run_parts:
                    logger.debug(
                        "Skipping %d pre-tool text chunks",
                        len(current_run_parts),
                    )
                current_run_parts = []

        full_answer = "".join(answer_parts)
        yield _sse({"type": "answer", "content": full_answer})
        yield _sse({"type": "done", "tools_used": list(tools_used)})

    except Exception as exc:
        logger.exception("Analyst chat failed: %s", question)
        # Yield any partial answer collected before the error
        partial = "".join(answer_parts)
        if partial:
            yield _sse({"type": "answer", "content": partial})
        yield _sse({"type": "error", "message": f"Query failed: {exc}"})
