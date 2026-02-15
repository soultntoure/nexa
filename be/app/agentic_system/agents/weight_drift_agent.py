"""Weight drift agent — autonomous weight drift investigator."""

from __future__ import annotations

import logging
from typing import Any

from app.agentic_system.base_agent import AgentConfig, BaseAgent
from app.agentic_system.prompts.weight_drift import WEIGHT_DRIFT_PROMPT
from app.agentic_system.schemas.background_audit import AgentSynthesisResult

logger = logging.getLogger(__name__)

FALLBACK_RESULT = {
    "plain_language": "Auto-generated drift summary (agent unavailable)",
    "analyst_notes": "Review weight drift statistics manually",
    "limitations": "Agent synthesis was not available for drift analysis",
    "uncertainty": "High — manual review required",
    "formal_pattern_name": "Weight Drift",
    "recommendations": [],
    "web_references": [],
    "clustering_notes": "",
    "sql_findings": [],
}


class WeightDriftAgent:
    """Wraps BaseAgent for autonomous weight drift investigation."""

    def __init__(self, tools: tuple = (), schema_docs: str = "") -> None:
        prompt = WEIGHT_DRIFT_PROMPT
        if schema_docs:
            prompt = prompt.replace(
                "## Database Schema (exact columns)", schema_docs,
            )
        config = AgentConfig(
            prompt=prompt,
            model="gemini-3-flash-preview",
            temperature=0.6,
            tools=tools,
            output_schema=AgentSynthesisResult,
            max_iterations=12,
        )
        self._agent = BaseAgent(config)

    async def analyze(
        self, evidence_text: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Analyze weight drift evidence.

        Returns (result_dict, tool_trace) tuple.
        """
        try:
            result, trace = await self._agent.invoke_verbose(evidence_text)
            if isinstance(result, AgentSynthesisResult):
                return result.model_dump(), trace
            return {"plain_language": str(result), **FALLBACK_RESULT}, trace
        except Exception:
            logger.warning("Drift agent failed, using fallback", exc_info=True)
            return {**FALLBACK_RESULT, "agent_fallback_used": True}, []
