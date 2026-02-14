"""Background audit agent — autonomous fraud pattern investigator."""

from __future__ import annotations

import logging
from typing import Any

from app.agentic_system.base_agent import AgentConfig, BaseAgent
from app.agentic_system.prompts.background_audit import SYNTHESIS_PROMPT
from app.agentic_system.schemas.background_audit import AgentSynthesisResult

logger = logging.getLogger(__name__)

FALLBACK_RESULT = {
    "plain_language": "Auto-generated summary (agent unavailable)",
    "analyst_notes": "Review cluster evidence manually",
    "limitations": "Agent synthesis was not available for this candidate",
    "uncertainty": "High — manual review required",
    "formal_pattern_name": "Unknown",
    "web_references": [],
    "clustering_notes": "",
    "sql_findings": [],
}


class BackgroundAuditAgent:
    """Owns a BaseAgent for autonomous fraud pattern investigation."""

    def __init__(self, tools: tuple = (), schema_docs: str = "") -> None:
        prompt = SYNTHESIS_PROMPT
        if schema_docs:
            prompt = prompt.replace("## Database Schema (exact columns)", schema_docs)
        config = AgentConfig(
            prompt=prompt,
            model="gemini-3-flash-preview",
            temperature=0.6,
            tools=tools,
            output_schema=AgentSynthesisResult,
            max_iterations=12,
        )
        self._agent = BaseAgent(config)

    async def synthesize_candidate(
        self, evidence_text: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Synthesize a pattern card from evidence text.

        Returns (result_dict, tool_trace) tuple.
        """
        try:
            result, trace = await self._agent.invoke_verbose(evidence_text)
            if isinstance(result, AgentSynthesisResult):
                return result.model_dump(), trace
            return {"plain_language": str(result), **FALLBACK_RESULT}, trace
        except Exception:
            logger.warning("Agent synthesis failed, using fallback", exc_info=True)
            return {**FALLBACK_RESULT, "agent_fallback_used": True}, []
