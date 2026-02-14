"""Investigator pipeline: rule engine -> all investigators -> triage verdict."""

import asyncio
import logging
import time
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agentic_system.schemas.indicators import IndicatorResult
from app.agentic_system.schemas.triage import (
    InvestigatorAssignment,
    InvestigatorResult,
    InvestigatorName,
    TriageResult,
)
from app.api.schemas.fraud.fraud_check import FraudCheckRequest
from app.core.calibration import build_effective_weights
from app.core.indicators import run_all_indicators
from app.config import get_settings
from app.core.scoring import (
    APPROVE_THRESHOLD,
    BLOCK_THRESHOLD,
    INDICATOR_WEIGHTS,
    ScoringResult,
    calculate_risk_score,
)
from app.data.db.models.customer_weight_profile import CustomerWeightProfile
from app.services.control.threshold_service import get_active_thresholds
from app.services.prefraud.signals.base import MAX_POSTURE_UPLIFT, POSTURE_UPLIFT_WEIGHT
from app.core.weight_context import INVESTIGATOR_INDICATORS, build_weight_context
from app.services.fraud.internals import (
    InvestigatorDataLoader,
    apply_verdict,
    build_investigation_data,
    build_rule_ctx,
    build_tools,
    format_indicators_for_llm,
    format_investigators_for_verdict,
    format_pattern_context,
    format_posture_context,
    persist_investigation,
)

logger = logging.getLogger(__name__)

MODEL = "gemini-3-flash-preview"
TRIAGE_MODEL = "gemini-3-flash-preview"
TRIAGE_TIMEOUT_S = 25.0
INVESTIGATOR_TIMEOUT_S = 25.0

ALL_INVESTIGATORS: list[InvestigatorName] = [
    "financial_behavior",
    "identity_access",
    "cross_account",
]


class InvestigatorService:
    """Runs rule engine -> all investigators -> triage verdict -> decision."""

    def __init__(
        self, session_factory: async_sessionmaker, sync_db_uri: str,
    ) -> None:
        self._session_factory = session_factory
        self._sync_db_uri = sync_db_uri
        self._loader = InvestigatorDataLoader(session_factory)

    async def investigate(self, request: FraudCheckRequest) -> dict:
        """Full pipeline: rules -> investigators -> triage verdict -> decision."""
        t0 = time.perf_counter()

        rule_ctx = build_rule_ctx(request)
        results, profile, threshold_config, posture, pattern_matches = (
            await self._load_all(rule_ctx, request.customer_id)
        )

        scoring, approve_thresh, block_thresh = self._score_rules(
            results, profile, threshold_config,
        )
        rule_elapsed = round(time.perf_counter() - t0, 3)

        posture_uplift = self._calculate_posture_uplift(posture)
        context = self._build_llm_context(results, scoring, request, posture, pattern_matches)
        weight_ctx = self._build_weight_context(profile)

        triage, findings, triage_elapsed = await self._resolve_triage(
            scoring, posture_uplift, approve_thresh, context, weight_ctx, profile,
        )

        decision, score = apply_verdict(
            scoring, triage, posture_uplift, approve_threshold=approve_thresh,
        )
        total = round(time.perf_counter() - t0, 2)
        evaluation_id = uuid.uuid4()

        investigation_data = build_investigation_data(
            triage, triage_elapsed, findings,
            rule_decision=scoring.decision, rule_score=scoring.composite_score,
            final_decision=decision, final_score=score,
            weight_profile=profile, posture=posture,
            posture_uplift=posture_uplift, pattern_matches=pattern_matches,
        )
        await persist_investigation(
            self._session_factory, evaluation_id, request, results, scoring,
            decision, score, total, investigation_data,
            approve_threshold=approve_thresh, block_threshold=block_thresh,
        )

        return self._build_result(
            evaluation_id, scoring, results, triage, triage_elapsed,
            findings, decision, score, rule_elapsed, total,
            approve_thresh, block_thresh, posture,
        )

    # ------------------------------------------------------------------
    # Pipeline steps (called from investigate)
    # ------------------------------------------------------------------

    async def _load_all(self, rule_ctx: dict, customer_id: str) -> tuple:
        """Load rule indicators + customer data in parallel."""
        return await asyncio.gather(
            run_all_indicators(rule_ctx, self._session_factory),
            self._loader.load_customer_profile(customer_id),
            get_active_thresholds(self._session_factory),
            self._loader.load_posture(customer_id),
            self._loader.load_pattern_matches(customer_id),
        )

    def _score_rules(
        self, results: list[IndicatorResult], profile, threshold_config,
    ) -> tuple[ScoringResult, float, float]:
        """Calculate risk score from rule indicators + calibrated weights."""
        approve = (
            threshold_config.approve_below / 100
            if threshold_config else APPROVE_THRESHOLD
        )
        block = (
            threshold_config.escalate_below / 100
            if threshold_config else BLOCK_THRESHOLD
        )
        effective_weights = (
            build_effective_weights(INDICATOR_WEIGHTS, profile.indicator_weights)
            if profile else None
        )
        scoring = calculate_risk_score(
            results, weights=effective_weights,
            approve_threshold=approve, block_threshold=block,
        )
        return scoring, approve, block

    def _calculate_posture_uplift(self, posture) -> float:
        """Compute posture uplift if enabled and posture is abnormal."""
        settings = get_settings()
        if (
            settings.POSTURE_INFLUENCE_ENABLED
            and posture
            and posture.posture != "normal"
        ):
            return min(
                posture.composite_score * POSTURE_UPLIFT_WEIGHT,
                MAX_POSTURE_UPLIFT,
            )
        return 0.0

    def _build_llm_context(
        self, results, scoring, request, posture, pattern_matches,
    ) -> str:
        """Assemble the LLM context string from indicators + posture + patterns."""
        context = format_indicators_for_llm(results, scoring, request)
        if posture:
            context += format_posture_context(posture)
        if pattern_matches:
            context += format_pattern_context(pattern_matches)
        return context

    def _build_weight_context(self, profile) -> str:
        """Build weight calibration context for LLM prompts."""
        return build_weight_context(
            profile.indicator_weights if profile else None,
            profile.blend_weights if profile else None,
        )

    async def _resolve_triage(
        self, scoring: ScoringResult, posture_uplift: float,
        approve_thresh: float, context: str, weight_ctx: str, profile,
    ) -> tuple[TriageResult, list[dict], float]:
        """Skip triage for obvious cases; run investigators + verdict otherwise."""
        adjusted = scoring.composite_score + posture_uplift
        effective = scoring.decision
        if scoring.decision == "approved" and adjusted >= approve_thresh:
            effective = "escalated"

        if effective in ("approved", "blocked"):
            return self._build_skip_triage(scoring, adjusted), [], 0.0

        findings, _ = await self._run_investigators(
            context, build_tools(self._sync_db_uri), weight_profile=profile,
        )
        verdict_ctx = context + "\n\n" + format_investigators_for_verdict(findings)
        triage, elapsed = await self._run_triage_verdict(verdict_ctx, weight_context=weight_ctx)
        triage.assignments = [
            InvestigatorAssignment(investigator=name, priority="medium")
            for name in ALL_INVESTIGATORS
        ]
        return triage, findings, elapsed

    def _build_skip_triage(self, scoring: ScoringResult, adjusted: float) -> TriageResult:
        """Create a synthetic triage result for auto-decided cases."""
        return TriageResult(
            constellation_analysis=f"Skipped — rule engine {scoring.decision}.",
            decision=scoring.decision,
            decision_reasoning=f"Auto-{scoring.decision} by rule engine (score {scoring.composite_score:.2f}).",
            confidence=1.0,
            risk_score=adjusted,
            assignments=[],
        )

    def _build_result(
        self, evaluation_id, scoring, results, triage, triage_elapsed,
        findings, decision, score, rule_elapsed, total,
        approve_thresh, block_thresh, posture,
    ) -> dict:
        """Assemble the final response dict."""
        return {
            "evaluation_id": evaluation_id,
            "scoring": scoring,
            "results": results,
            "triage": triage,
            "triage_elapsed_s": triage_elapsed,
            "findings": findings,
            "decision": decision,
            "risk_score": score,
            "rule_engine_elapsed_s": rule_elapsed,
            "total_elapsed_s": total,
            "approve_threshold": approve_thresh,
            "block_threshold": block_thresh,
            "posture": posture,
        }

    # ------------------------------------------------------------------
    # LLM runners
    # ------------------------------------------------------------------

    async def _run_triage_verdict(
        self, context: str, weight_context: str = "",
    ) -> tuple[TriageResult, float]:
        """Single LLM call to synthesize verdict from rules + investigator findings."""
        from app.agentic_system.base_agent import AgentConfig, BaseAgent
        from app.agentic_system.prompts.triage import TRIAGE_VERDICT_PROMPT

        prompt = TRIAGE_VERDICT_PROMPT.format(weight_context=weight_context)
        agent = BaseAgent(AgentConfig(
            prompt=prompt,
            model=TRIAGE_MODEL,
            output_schema=TriageResult,
            tools=(),
            timeout=TRIAGE_TIMEOUT_S,
            thinking_level="low",
            max_tokens=512,
        ))

        t0 = time.perf_counter()
        try:
            result = await agent.invoke(context)
            if isinstance(result, TriageResult):
                return result, round(time.perf_counter() - t0, 3)
            logger.warning(
                "Triage verdict returned non-structured type=%s value=%s",
                type(result).__name__, str(result)[:500],
            )
        except Exception as exc:
            raw = getattr(exc, "llm_output", None) or getattr(exc, "observation", None)
            logger.error(
                "Triage verdict failed: %s: %s | raw_output=%s",
                type(exc).__name__, exc, str(raw)[:500] if raw else "N/A",
                exc_info=True,
            )

        fallback = TriageResult(
            constellation_analysis="Triage verdict failed — defaulting to escalation.",
            decision="escalated",
            decision_reasoning="Verdict LLM failed; escalating for human review.",
            confidence=0.0,
            risk_score=0.5,
        )
        return fallback, round(time.perf_counter() - t0, 3)

    async def _run_investigators(
        self,
        context: str,
        tools: tuple,
        weight_profile: CustomerWeightProfile | None = None,
    ) -> tuple[list[dict], float]:
        """Run all 3 investigators in parallel."""
        t0 = time.perf_counter()
        assignments = [
            InvestigatorAssignment(investigator=name, priority="medium")
            for name in ALL_INVESTIGATORS
        ]
        tasks = [
            self._run_single_investigator(
                a, context, tools, weight_profile=weight_profile,
            )
            for a in assignments
        ]
        results = await asyncio.gather(*tasks)
        return list(results), round(time.perf_counter() - t0, 3)

    async def _run_single_investigator(
        self,
        assignment: InvestigatorAssignment,
        context: str,
        tools: tuple,
        weight_profile: CustomerWeightProfile | None = None,
    ) -> dict:
        """Run one investigator with rule engine context."""
        from app.agentic_system.base_agent import AgentConfig, BaseAgent
        from app.agentic_system.prompts.investigators import (
            build_investigator_prompt,
        )

        relevant = INVESTIGATOR_INDICATORS.get(assignment.investigator)
        filtered_ctx = build_weight_context(
            weight_profile.indicator_weights if weight_profile else None,
            weight_profile.blend_weights if weight_profile else None,
            relevant_indicators=relevant,
        )
        prompt = build_investigator_prompt(
            assignment.investigator, weight_context=filtered_ctx,
        )
        agent = BaseAgent(AgentConfig(
            prompt=prompt,
            model=MODEL,
            output_schema=InvestigatorResult,
            tools=tools,
            timeout=INVESTIGATOR_TIMEOUT_S,
            thinking_level="low",
            max_tokens=512,
            max_iterations=3,
        ))

        t0 = time.perf_counter()
        try:
            result, _trace = await agent.invoke_verbose(context)
            elapsed = round(time.perf_counter() - t0, 3)
            if isinstance(result, InvestigatorResult):
                return {"result": result, "elapsed_s": elapsed}
            logger.warning(
                "Investigator %s returned non-structured type=%s value=%s",
                assignment.investigator, type(result).__name__, str(result)[:500],
            )
            return {
                "result": None,
                "error": f"Non-structured output: {type(result).__name__}",
                "elapsed_s": elapsed,
            }
        except Exception as exc:
            raw = getattr(exc, "llm_output", None) or getattr(exc, "observation", None)
            logger.error(
                "Investigator %s failed: %s: %s | raw_output=%s",
                assignment.investigator, type(exc).__name__, exc,
                str(raw)[:500] if raw else "N/A",
                exc_info=True,
            )
            return {
                "result": None,
                "error": str(exc),
                "elapsed_s": round(time.perf_counter() - t0, 3),
            }
