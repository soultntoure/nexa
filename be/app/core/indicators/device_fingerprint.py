"""Device Fingerprint indicator — cross-account sharing and trust."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agentic_system.schemas.indicators import IndicatorResult
from app.core.indicators.base import BaseIndicator
from app.data.db.repositories.device_repository import DeviceRepository


class DeviceFingerprintIndicator(BaseIndicator):
    name = "device_fingerprint"
    weight = 1.3

    async def evaluate(
        self, ctx: dict, session: AsyncSession,
    ) -> IndicatorResult:
        fp = ctx.get("device_fingerprint", "")
        repo = DeviceRepository(session)
        row = await repo.get_fingerprint_risk(ctx["customer_id"], fp)

        if not row:
            evidence = {"fingerprint": fp, "known": False}
            from app.core.indicators._reasoning import build_device_reasoning
            return IndicatorResult(
                indicator_name="device_fingerprint",
                score=0.4,
                confidence=1.0,
                reasoning=build_device_reasoning(evidence, 0.4),
                evidence=evidence,
            )

        score, reasoning, evidence = _compute_score(row)
        return IndicatorResult(
            indicator_name="device_fingerprint",
            score=score,
            confidence=1.0,
            reasoning=reasoning,
            evidence=evidence,
        )


def _compute_score(row: dict) -> tuple[float, str, dict]:
    """Score based on trust, age, and cross-account sharing."""
    is_trusted = bool(row["is_trusted"])
    age_days = float(row["device_age_days"] or 0)
    shared = int(row["shared_account_count"] or 1)

    evidence = {
        "is_trusted": is_trusted,
        "device_age_days": round(age_days, 1),
        "shared_account_count": shared,
    }

    score = 0.0
    reasons = []

    if shared >= 3:
        score += 0.7
        reasons.append(f"Device shared across {shared} accounts")
    elif shared == 2:
        score += 0.4
        reasons.append("Device shared with 1 other account")

    if not is_trusted:
        score += 0.25
        reasons.append("Device not trusted")

    if age_days < 1:
        score += 0.25
        reasons.append("Brand new device (<1d)")
    elif age_days < 7:
        score += 0.15
        reasons.append(f"Recent device ({age_days:.0f}d)")

    score = min(score, 1.0)
    from app.core.indicators._reasoning import build_device_reasoning
    return round(score, 2), build_device_reasoning(evidence, round(score, 2)), evidence
