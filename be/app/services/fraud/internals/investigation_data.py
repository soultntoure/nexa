"""Serialize triage + investigator findings into JSONB for DB storage."""

from app.agentic_system.schemas.triage import TriageResult
from app.config import get_settings
from app.data.db.models.customer_risk_posture import CustomerRiskPosture
from app.data.db.models.customer_weight_profile import CustomerWeightProfile


def build_investigation_data(
    triage: TriageResult,
    triage_elapsed: float,
    findings: list[dict],
    rule_decision: str,
    rule_score: float,
    final_decision: str,
    final_score: float,
    weight_profile: CustomerWeightProfile | None = None,
    posture: CustomerRiskPosture | None = None,
    posture_uplift: float = 0.0,
    pattern_matches: list | None = None,
) -> dict:
    """Serialize triage + investigator findings for DB storage."""
    settings = get_settings()

    investigators = []
    for f in findings:
        result = f.get("result")
        if result is None:
            continue
        investigators.append({
            "name": result.investigator_name,
            "score": result.score,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "elapsed_s": f["elapsed_s"],
        })

    data = {
        "rule_engine": {
            "decision": rule_decision,
            "score": round(rule_score, 4),
        },
        "posture": _build_posture_data(posture, posture_uplift, settings),
        "patterns": _build_patterns_data(pattern_matches or [], settings),
        "final_decision": {
            "decision": final_decision,
            "score": round(final_score, 4),
        },
        "triage": {
            "constellation_analysis": triage.constellation_analysis,
            "decision": triage.decision,
            "decision_reasoning": triage.decision_reasoning,
            "confidence": triage.confidence,
            "risk_score": triage.risk_score,
            "assignments": [
                {"investigator": a.investigator, "priority": a.priority}
                for a in triage.assignments
            ],
            "elapsed_s": triage_elapsed,
        },
        "investigators": investigators,
    }
    if weight_profile:
        data["weight_calibration"] = {
            "indicator_multipliers": weight_profile.indicator_weights,
            "blend_weights": weight_profile.blend_weights,
            "recalculated_at": weight_profile.recalculated_at.isoformat(),
        }
    return data


def _build_posture_data(
    posture: CustomerRiskPosture | None,
    posture_uplift: float,
    settings,
) -> dict:
    """Build posture section for investigation_data JSONB."""
    if posture is None:
        return {
            "state": None,
            "score": None,
            "top_reasons": [],
            "influence_enabled": settings.POSTURE_INFLUENCE_ENABLED,
            "uplift_applied": 0.0,
        }

    evidence = posture.signal_evidence or {}
    return {
        "state": posture.posture,
        "score": round(posture.composite_score, 4),
        "top_reasons": evidence.get("top_reasons", []),
        "influence_enabled": settings.POSTURE_INFLUENCE_ENABLED,
        "uplift_applied": round(posture_uplift, 4),
    }


def _build_patterns_data(matches: list, settings) -> dict:
    """Build patterns section for investigation_data JSONB."""
    return {
        "match_count": len(matches),
        "scoring_enabled": settings.PATTERN_SCORING_ENABLED,
        "matches": [
            {
                "pattern_type": m.pattern.pattern_type,
                "confidence": m.confidence,
                "evidence": m.evidence,
            }
            for m in matches
        ],
    }
