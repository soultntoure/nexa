"""Seed background audit demo — 1 showcase run, 3 candidates, rich evidence."""

import hashlib
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models.audit_candidate import AuditCandidate
from app.data.db.models.audit_candidate_evidence import AuditCandidateEvidence
from app.data.db.models.audit_run import AuditRun
from app.data.db.models.audit_text_unit import AuditTextUnit

from .audit_pattern_cards import (
    PATTERN_CARD_ATO, PATTERN_CARD_DEPOSIT_RUN, PATTERN_CARD_MULE,
)
from .constants import _ago, _id


async def _seed_audit_patterns(s: AsyncSession) -> None:
    """Seed 1 completed audit run with 3 candidates + evidence + text units."""
    # Flush prior seeders so evaluation FKs exist for text units
    await s.flush()

    run_id = "audit-run-seed-001"

    s.add(_build_run(run_id))
    _add_candidate_ato(s, run_id)
    _add_candidate_deposit_run(s, run_id)
    _add_candidate_mule(s, run_id)


def _build_run(run_id: str) -> AuditRun:
    """Build the showcase audit run."""
    return AuditRun(
        id=_id("audit.run.seed"),
        run_id=run_id,
        status="completed",
        run_mode="full",
        config_snapshot={
            "min_quality": 0.5, "max_candidates": 10, "lookback_days": 30,
        },
        counters={
            "units_extracted": 67, "clusters_found": 8, "candidates_generated": 3,
        },
        timings={
            "extract": 2.1, "embed": 1.4, "cluster": 0.9, "score": 0.6, "total": 5.0,
        },
        started_at=_ago(hours=6),
        completed_at=_ago(hours=6) + timedelta(seconds=5),
        last_heartbeat_at=_ago(hours=6) + timedelta(seconds=5),
        idempotency_key="seed-audit-run-001",
    )


def _add_candidate_ato(s: AsyncSession, run_id: str) -> None:
    """Candidate 1: Identity Access — Impossible Travel + ATO (Nina)."""
    cand = "CAND-SEED-001"
    eval_id, wd_id = _id("nina.eval"), _id("nina.wd.pending")

    s.add(AuditCandidate(
        id=_id("audit.candidate.1"), candidate_id=cand, run_id=run_id,
        status="pending", title="Identity Access: Impossible Travel + New Device",
        cluster_id="cluster-seed-ia-01", cluster_fingerprint="fp-ia-impossible-travel",
        novelty_status="new", confidence=0.83, support_events=18,
        support_accounts=3, quality_score=0.67, pattern_card=PATTERN_CARD_ATO,
        created_at=_ago(hours=6), updated_at=_ago(hours=6),
    ))

    _tu(s, "TU-SEED-001", eval_id, wd_id, "investigator", "identity_access",
        "Geographic impossibility detected: last known IP in Kyiv (UKR) "
        "35 minutes before request from [CITY_REDACTED] (BRA). New macOS 14 "
        "device appeared at destination — never seen on this account. "
        "Combined with 4x normal withdrawal amount, this strongly suggests "
        "account takeover via stolen credentials.",
        0.78, 0.83)
    _tu(s, "TU-SEED-002", eval_id, wd_id, "triage", "triage_router",
        "Constellation shows geographic + device + amount anomaly converging. "
        "IP transition Kyiv→[CITY_REDACTED] in 35min is physically impossible. "
        "New device at destination is a hallmark of credential-based ATO.",
        0.75, 0.80)
    _tu(s, "TU-SEED-003", eval_id, wd_id, "investigator", "financial_behavior",
        "3 rapid funding cycles in 3 days (deposit $800 → withdraw $750 "
        "within ~4 hours each). Current $2000 withdrawal is 4x her normal "
        "range. Pattern shifted from structured cycling to bulk extraction.",
        0.72, 0.78)

    _ev(s, cand, "TU-SEED-001", "supporting", 1,
        "Identity investigator flagged impossible travel Kyiv→São Paulo in 35min.",
        {"confidence": 0.83, "score": 0.78, "source_name": "identity_access"})
    _ev(s, cand, "TU-SEED-002", "triage", 2,
        "Triage constellation: geographic + device + amount anomaly converge.",
        {"confidence": 0.80, "score": 0.75, "source_name": "triage_router"})
    _ev(s, cand, "TU-SEED-003", "supporting", 3,
        "Financial investigator found 3 rapid-funding cycles preceding ATO.",
        {"confidence": 0.78, "score": 0.72, "source_name": "financial_behavior"})


def _add_candidate_deposit_run(s: AsyncSession, run_id: str) -> None:
    """Candidate 2: Financial Behavior — Deposit & Run + Shared Device."""
    cand = "CAND-SEED-002"
    v_eval, v_wd = _id("victor.eval"), _id("victor.wd.pending")
    a_eval, a_wd = _id("ahmed.eval"), _id("ahmed.wd.pending")

    s.add(AuditCandidate(
        id=_id("audit.candidate.2"), candidate_id=cand, run_id=run_id,
        status="pending", title="Financial Behavior: Deposit & Run + Shared Device",
        cluster_id="cluster-seed-fb-01", cluster_fingerprint="fp-fb-deposit-run",
        novelty_status="new", confidence=0.79, support_events=15,
        support_accounts=4, quality_score=0.62, pattern_card=PATTERN_CARD_DEPOSIT_RUN,
        created_at=_ago(hours=6), updated_at=_ago(hours=6),
    ))

    _tu(s, "TU-SEED-004", v_eval, v_wd, "investigator", "financial_behavior",
        "Classic deposit-and-run: [CUSTOMER] deposited $3k, placed 1 token "
        "trade ($10, 15 seconds), now withdrawing $2990 (>99% of deposits). "
        "Account only 5 days old. Device shared with CUST-012.",
        0.82, 0.79)
    _tu(s, "TU-SEED-005", a_eval, a_wd, "investigator", "cross_account",
        "Fraud ring confirmed: CUST-013 and CUST-014 share device fingerprint "
        "deadbeef*, same IP 41.44.55.*, and third-party recipient "
        "'[NAME_REDACTED]'. Coordinated withdrawals within 10 minutes.",
        0.85, 0.88)
    _tu(s, "TU-SEED-006", v_eval, v_wd, "constellation_analysis", "triage_router",
        "Four accounts exhibit the 'new everything' constellation: new account "
        "+ new device + no meaningful trading + near-full withdrawal. Two pairs "
        "linked by shared device fingerprints (a1b2c3d4 and deadbeef).",
        0.80, 0.82)

    _ev(s, cand, "TU-SEED-004", "supporting", 1,
        "Financial investigator: deposit-and-run on Victor ($2990, 99% ratio).",
        {"confidence": 0.79, "score": 0.82, "source_name": "financial_behavior"})
    _ev(s, cand, "TU-SEED-005", "investigator", 2,
        "Cross-account confirmed shared device + IP + recipient ring.",
        {"confidence": 0.88, "score": 0.85, "source_name": "cross_account"})
    _ev(s, cand, "TU-SEED-006", "triage", 3,
        "Triage: 'new everything' constellation across 4 linked accounts.",
        {"confidence": 0.82, "score": 0.80, "source_name": "triage_router"})


def _add_candidate_mule(s: AsyncSession, run_id: str) -> None:
    """Candidate 3: Cross-Account — Mule Network (Priya + ring)."""
    cand = "CAND-SEED-003"
    p_eval, p_wd = _id("priya.eval"), _id("priya.wd.pending")

    s.add(AuditCandidate(
        id=_id("audit.candidate.3"), candidate_id=cand, run_id=run_id,
        status="pending", title="Cross-Account: Mule Network Expansion",
        cluster_id="cluster-seed-ca-01", cluster_fingerprint="fp-ca-mule-network",
        novelty_status="new", confidence=0.87, support_events=22,
        support_accounts=5, quality_score=0.74, pattern_card=PATTERN_CARD_MULE,
        created_at=_ago(hours=6), updated_at=_ago(hours=6),
    ))

    _tu(s, "TU-SEED-007", p_eval, p_wd, "investigator", "cross_account",
        "Device fingerprint deadbeef* matches CUST-013 ([NAME_REDACTED]) and "
        "CUST-014 ([NAME_REDACTED]) — confirmed fraud ring. CUST-020 is a new "
        "mule node: 3-day account, zero trades, same third-party recipient. "
        "IP in ring cluster (41.44.55.*).",
        0.92, 0.90)
    _tu(s, "TU-SEED-008", p_eval, p_wd, "investigator", "financial_behavior",
        "Pure pass-through pattern: $5000 deposited across 2 transactions, "
        "$4800 withdrawal (96%) with zero trades. 3-day account lifetime. "
        "Mule accounts serve as layering step for ring proceeds.",
        0.85, 0.87)
    _tu(s, "TU-SEED-009", p_eval, p_wd, "triage", "triage_router",
        "Network expansion detected: existing 2-node ring (CUST-013/014) now "
        "has 3rd mule (CUST-020). Shared device + shared recipient + IP "
        "proximity. The ring is actively recruiting pass-through accounts.",
        0.88, 0.89)

    _ev(s, cand, "TU-SEED-007", "supporting", 1,
        "Cross-account: device + recipient link to Ahmed/Fatima fraud ring.",
        {"confidence": 0.90, "score": 0.92, "source_name": "cross_account"})
    _ev(s, cand, "TU-SEED-008", "supporting", 2,
        "Financial: pure pass-through — $5k in, $4.8k out, zero trades.",
        {"confidence": 0.87, "score": 0.85, "source_name": "financial_behavior"})
    _ev(s, cand, "TU-SEED-009", "triage", 3,
        "Triage: network expansion — ring growing from 2 to 3 mule nodes.",
        {"confidence": 0.89, "score": 0.88, "source_name": "triage_router"})


# ── Helpers ──

def _tu(
    s: AsyncSession, uid: str, eval_id, wd_id,
    src_type: str, src_name: str, text: str,
    score: float, confidence: float,
) -> None:
    """Add a single AuditTextUnit."""
    s.add(AuditTextUnit(
        id=_id(f"atu.{uid}"), unit_id=uid,
        evaluation_id=eval_id, withdrawal_id=wd_id,
        source_type=src_type, source_name=src_name,
        text_masked=text,
        text_hash=hashlib.sha256(text.encode()).hexdigest()[:64],
        score=score, confidence=confidence,
        decision_snapshot={"source": "seed"},
        embedding_model_name="text-embedding-004",
        vector_status="completed",
    ))


def _ev(
    s: AsyncSession, cand_id: str, unit_id: str,
    ev_type: str, rank: int, snippet: str, meta: dict,
) -> None:
    """Add a single AuditCandidateEvidence row."""
    s.add(AuditCandidateEvidence(
        id=_id(f"ace.{cand_id}.{unit_id}"),
        candidate_id=cand_id, unit_id=unit_id,
        evidence_type=ev_type, rank=rank,
        snippet=snippet, metadata_=meta,
    ))
