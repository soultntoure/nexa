"""Tavily web search tool scoped to fraud typology research."""

from __future__ import annotations

import logging
from typing import Any
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)


def create_web_search_tool(api_key: str) -> Any | None:
    """Create a Tavily web search tool if available and configured."""
    if not api_key:
        logger.info("Web search tool unavailable (no API key)")
        return None

    try:
        from langchain_tavily import TavilySearch
    except ImportError:
        logger.info("Web search tool unavailable (langchain-tavily not installed)")
        return None

    return TavilySearch(
        name="fraud_web_search",
        description=(
            "Search the web for known fraud typologies, regulatory alerts, "
            "and published fraud case studies. Use to corroborate discovered "
            "patterns against publicly documented fraud schemes."
        ),
        max_results=5,
        search_depth="advanced",
        topic="finance",
        tavily_api_key=api_key,
    )
