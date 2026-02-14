"""
Review-queue data access — pending withdrawals needing officer review.

Methods:
- get_review_queue(skip, limit) -> list[Row]
- count_review_queue() -> int

Query logic: pending withdrawals with latest evaluation decision
IN ('escalated', 'blocked') and no officer decision yet.
"""

from __future__ import annotations

from sqlalchemy import Select, case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.customer import Customer
from app.data.db.models.evaluation import Evaluation
from app.data.db.models.indicator_result import IndicatorResult
from app.data.db.models.withdrawal import Withdrawal
from app.data.db.models.withdrawal_decision import WithdrawalDecision


class QueueRepository:
    """Read-only repository for the officer review queue."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_review_queue(
        self, skip: int = 0, limit: int = 20,
    ) -> list[dict]:
        """Return pending withdrawals needing review, richest risk first."""
        try:
            stmt = self._base_query().offset(skip).limit(limit)
            result = await self.session.execute(stmt)
            rows = result.mappings().all()
            return await self._attach_indicators(list(rows))
        except SQLAlchemyError as e:
            raise RuntimeError("Error fetching review queue") from e

    async def count_review_queue(self) -> int:
        """Total items in the queue (for pagination)."""
        try:
            latest = self._latest_eval_subquery()
            stmt = (
                select(func.count(Withdrawal.id))
                .join(Customer, Customer.id == Withdrawal.customer_id)
                .join(Evaluation, Evaluation.withdrawal_id == Withdrawal.id)
                .outerjoin(
                    WithdrawalDecision,
                    WithdrawalDecision.withdrawal_id == Withdrawal.id,
                )
                .where(
                    Evaluation.checked_at == latest,
                    Evaluation.decision.in_(["escalated", "blocked"]),
                    WithdrawalDecision.id.is_(None),
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            raise RuntimeError("Error counting review queue") from e

    # ── private helpers ──

    @staticmethod
    def _latest_eval_subquery() -> Select:
        """Scalar subquery: latest checked_at per withdrawal."""
        return (
            select(func.max(Evaluation.checked_at))
            .where(Evaluation.withdrawal_id == Withdrawal.id)
            .correlate(Withdrawal)
            .scalar_subquery()
        )

    def _base_query(self) -> Select:
        """Core SELECT for the review queue."""
        latest = self._latest_eval_subquery()
        return (
            select(
                Withdrawal.id.label("withdrawal_id"),
                Withdrawal.amount,
                Withdrawal.currency,
                Withdrawal.requested_at,
                Customer.external_id.label("customer_id"),
                Customer.name.label("customer_name"),
                Customer.email.label("customer_email"),
                Evaluation.id.label("evaluation_id"),
                Evaluation.decision,
                Evaluation.composite_score,
                Evaluation.risk_level,
                Evaluation.summary,
                Evaluation.checked_at.label("evaluated_at"),
                Evaluation.gray_zone_used,
                Evaluation.gray_zone_decision,
                Evaluation.gray_zone_reasoning,
                Evaluation.investigation_data,
            )
            .join(Customer, Customer.id == Withdrawal.customer_id)
            .join(Evaluation, Evaluation.withdrawal_id == Withdrawal.id)
            .outerjoin(
                WithdrawalDecision,
                WithdrawalDecision.withdrawal_id == Withdrawal.id,
            )
            .where(
                Evaluation.checked_at == latest,
                Evaluation.decision.in_(["escalated", "blocked"]),
                WithdrawalDecision.id.is_(None),
            )
            .order_by(
                case(
                    (Evaluation.decision == "blocked", 0),
                    (Evaluation.decision == "escalated", 1),
                    else_=2,
                ),
                Evaluation.composite_score.desc(),
            )
        )

    async def _attach_indicators(
        self, rows: list[dict],
    ) -> list[dict]:
        """Fetch indicator_results for each evaluation and merge."""
        if not rows:
            return []

        eval_ids = [r["evaluation_id"] for r in rows]
        stmt = (
            select(IndicatorResult)
            .where(IndicatorResult.evaluation_id.in_(eval_ids))
            .order_by(IndicatorResult.score.desc())
        )
        result = await self.session.execute(stmt)
        indicators = result.scalars().all()

        grouped: dict[str, list] = {}
        for ind in indicators:
            key = str(ind.evaluation_id)
            grouped.setdefault(key, []).append(ind)

        enriched = []
        for row in rows:
            row_dict = dict(row)
            row_dict["indicators"] = grouped.get(
                str(row["evaluation_id"]), [],
            )
            enriched.append(row_dict)

        return enriched
