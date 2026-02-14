"""Recipient Analysis indicator — name match and cross-account usage."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agentic_system.schemas.indicators import IndicatorResult
from app.core.indicators.base import BaseIndicator
from app.data.db.repositories.withdrawal_repository import WithdrawalRepository


class RecipientIndicator(BaseIndicator):
    name = "recipient"
    weight = 1.0

    async def evaluate(
        self, ctx: dict, session: AsyncSession,
    ) -> IndicatorResult:
        recipient_name = ctx.get("recipient_name", "")
        recipient_account = ctx.get("recipient_account", "")

        repo = WithdrawalRepository(session)
        row = await repo.get_recipient_info(
            ctx["customer_id"], recipient_account,
        )

        if not row:
            return IndicatorResult(
                indicator_name="recipient",
                score=0.3,
                confidence=1.0,
                reasoning="Customer information could not be retrieved for recipient analysis.",
                evidence={},
            )

        score, reasoning, evidence = _compute_score(
            row, recipient_name,
        )
        return IndicatorResult(
            indicator_name="recipient",
            score=score,
            confidence=1.0,
            reasoning=reasoning,
            evidence=evidence,
        )


def _compute_score(
    row: dict, recipient_name: str,
) -> tuple[float, str, dict]:
    """Score based on name match, cross-account, and history."""
    customer_name = str(row["customer_name"] or "")
    cross_accounts = int(row["cross_account_count"] or 0)
    history = int(row["history_count"] or 0)
    name_match = customer_name.lower().strip() == recipient_name.lower().strip()

    evidence = {
        "name_match": name_match,
        "cross_account_count": cross_accounts,
        "history_with_recipient": history,
    }

    score = 0.0
    reasons = []

    if not name_match:
        score += 0.3
        reasons.append(f"Name mismatch: '{recipient_name}' vs '{customer_name}'")

    if cross_accounts >= 3:
        score += 0.4
        reasons.append(f"Recipient used by {cross_accounts} accounts")
    elif cross_accounts == 2:
        score += 0.2
        reasons.append("Recipient used by 2 accounts")

    if history == 0:
        score += 0.2
        reasons.append("First-time recipient")

    score = min(score, 1.0)
    from app.core.indicators._reasoning import build_recipient_reasoning
    return round(score, 2), build_recipient_reasoning(evidence, round(score, 2), recipient_name), evidence
