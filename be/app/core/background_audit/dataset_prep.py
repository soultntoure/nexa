"""Dataset preparation utilities for background-audit text pipelines."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.data.db.models.evaluation import Evaluation
from app.data.db.models.withdrawal import Withdrawal

EMAIL_RE = re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b")
IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
ACCOUNT_RE = re.compile(r"\b[A-Z]{2,5}-?\d{3,}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{4}\b")

MIN_TEXT_LENGTH = 20
MAX_TEXT_LENGTH = 5000
PII_PATTERNS = [EMAIL_RE, IP_RE, SSN_RE, PHONE_RE]


@dataclass(frozen=True)
class RunWindow:
    """Time window for a background-audit run."""

    start: datetime
    end: datetime
    lookback_days: int


def build_cohort_query(start: datetime, end: datetime):
    """Build query for confirmed-fraud evaluations in time window."""
    return (
        select(Evaluation)
        .join(Withdrawal, Withdrawal.id == Evaluation.withdrawal_id)
        .options(joinedload(Evaluation.withdrawal))
        .where(Withdrawal.is_fraud.is_(True))
        .where(Evaluation.checked_at >= start)
        .where(Evaluation.checked_at <= end)
        .order_by(Evaluation.checked_at.desc())
    )


def extract_reasoning_units(
    evaluation_id: str,
    withdrawal_id: str,
    investigation_data: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Extract triage + investigator reasoning text units."""
    if not investigation_data:
        return []

    units: list[dict[str, Any]] = []
    idx = 0

    triage = investigation_data.get("triage") or {}
    analysis = triage.get("constellation_analysis", "")
    if analysis:
        units.append(
            {
                "evaluation_id": evaluation_id,
                "withdrawal_id": withdrawal_id,
                "source_type": "triage",
                "source_name": "constellation_analysis",
                "text": analysis,
                "score": None,
                "confidence": None,
                "index": idx,
            }
        )
        idx += 1

    for inv in investigation_data.get("investigators", []):
        reasoning = inv.get("reasoning", "")
        if not reasoning:
            continue
        units.append(
            {
                "evaluation_id": evaluation_id,
                "withdrawal_id": withdrawal_id,
                "source_type": "investigator",
                "source_name": inv.get("name", "unknown"),
                "text": reasoning,
                "score": inv.get("score"),
                "confidence": inv.get("confidence"),
                "index": idx,
            }
        )
        idx += 1

    return units


def normalize_text(text: str) -> str:
    """Normalize whitespace and strip control characters."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
    return text.strip()


def mask_pii(text: str) -> str:
    """PII masking disabled — all identifiers kept visible."""
    return text


def validate_quality(text: str) -> bool:
    """Check minimum quality threshold for reasoning text."""
    if len(text) < MIN_TEXT_LENGTH or len(text) > MAX_TEXT_LENGTH:
        return False
    if len(text.split()) < 5:
        return False
    return True


def compute_text_hash(text: str) -> str:
    """Compute SHA256 hash for text dedupe."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_unit_id(evaluation_id: str, source_type: str, index: int) -> str:
    """Compute deterministic unit id from source identity."""
    key = f"{evaluation_id}|{source_type}|{index}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def scan_text_for_pii(text: str) -> bool:
    """PII scanning disabled."""
    return False


def generate_run_id() -> str:
    """Generate readable run id like audit_YYYYMMDD_HHMMSS_ab12cd34."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"audit_{ts}_{suffix}"


def compute_run_fingerprint(window: RunWindow, run_mode: str) -> str:
    """Stable idempotency key for the same window and mode."""
    payload = f"{window.start.isoformat()}|{window.end.isoformat()}|{run_mode}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def compute_window(lookback_days: int) -> RunWindow:
    """Compute UTC window [now-lookback_days, now]."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    return RunWindow(start=start, end=end, lookback_days=lookback_days)


def validate_window(window: RunWindow) -> bool:
    """Validate run window bounds and max lookback."""
    if window.start >= window.end:
        return False
    if (window.end - window.start).days > 365:
        return False
    return True
