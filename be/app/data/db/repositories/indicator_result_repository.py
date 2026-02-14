"""
IndicatorResult CRUD operations.

Contains:
- IndicatorResultRepository class (takes AsyncSession)
  - get_by_id(id: UUID) -> IndicatorResult | None
  - get_by_withdrawal(withdrawal_id: UUID) -> list[IndicatorResult]
  - get_by_indicator_name(indicator_name: str, limit: int) -> list[IndicatorResult]
  - get_high_scores(threshold: float, limit: int) -> list[IndicatorResult]
  - get_avg_score_by_indicator() -> dict

Rules: async only, expunge before return.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.evaluation import Evaluation
from app.data.db.models.indicator_result import IndicatorResult
from app.data.db.repositories.base_repository import BaseRepository


class IndicatorResultRepository(BaseRepository[IndicatorResult]):
    """Repository for IndicatorResult entity with analytics and aggregation methods."""

    model_class = IndicatorResult

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_withdrawal(
        self, withdrawal_id: uuid.UUID
    ) -> list[IndicatorResult]:
        """
        Get all indicator results for a withdrawal.
        
        Args:
            withdrawal_id: UUID of the withdrawal
            
        Returns:
            List of detached IndicatorResults
        """
        try:
            stmt = select(IndicatorResult).where(
                IndicatorResult.withdrawal_id == withdrawal_id
            ).order_by(IndicatorResult.created_at.desc())
            result = await self.session.execute(stmt)
            indicators = list(result.scalars().all())
            
            for indicator in indicators:
                self._expunge(indicator)
            
            return indicators
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving indicators for withdrawal {withdrawal_id}"
            ) from e

    async def get_by_evaluation_id(
        self, evaluation_id: uuid.UUID
    ) -> list[IndicatorResult]:
        """Get indicator results for one evaluation run."""
        try:
            stmt = (
                select(IndicatorResult)
                .where(IndicatorResult.evaluation_id == evaluation_id)
                .order_by(IndicatorResult.created_at.asc())
            )
            result = await self.session.execute(stmt)
            indicators = list(result.scalars().all())

            for indicator in indicators:
                self._expunge(indicator)

            return indicators
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving indicators for evaluation {evaluation_id}"
            ) from e

    async def get_latest_evaluation_id(
        self, withdrawal_id: uuid.UUID
    ) -> uuid.UUID | None:
        """Get the latest evaluation id for a withdrawal."""
        try:
            stmt = (
                select(Evaluation.id)
                .where(Evaluation.withdrawal_id == withdrawal_id)
                .order_by(Evaluation.checked_at.desc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving latest evaluation for withdrawal {withdrawal_id}"
            ) from e

    async def get_by_indicator_name(
        self, indicator_name: str, limit: int = 100
    ) -> list[IndicatorResult]:
        """
        Get results for a specific indicator across all withdrawals.
        
        Args:
            indicator_name: Name of the indicator
            limit: Maximum number of results to return
            
        Returns:
            List of detached IndicatorResults
        """
        try:
            stmt = (
                select(IndicatorResult)
                .where(IndicatorResult.indicator_name == indicator_name)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            indicators = list(result.scalars().all())
            
            for indicator in indicators:
                self._expunge(indicator)
            
            return indicators
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving results for indicator {indicator_name}"
            ) from e

    async def get_high_scores(
        self, threshold: float = 0.7, limit: int = 100
    ) -> list[IndicatorResult]:
        """
        Get indicator results with scores above threshold (high risk).
        
        Args:
            threshold: Score threshold (0.0-1.0)
            limit: Maximum number of results to return
            
        Returns:
            List of detached IndicatorResults with high scores
        """
        try:
            stmt = (
                select(IndicatorResult)
                .where(IndicatorResult.score >= threshold)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            indicators = list(result.scalars().all())
            
            for indicator in indicators:
                self._expunge(indicator)
            
            return indicators
        except SQLAlchemyError as e:
            raise RuntimeError("Error retrieving high score indicators") from e

    async def get_avg_score_by_indicator(self) -> dict[str, Any]:
        """
        Get average scores grouped by indicator name for calibration.
        
        Returns:
            Dictionary mapping indicator_name to average score
        """
        try:
            stmt = select(
                IndicatorResult.indicator_name,
                func.avg(IndicatorResult.score).label("avg_score"),
                func.count(IndicatorResult.id).label("count")
            ).group_by(IndicatorResult.indicator_name)
            
            result = await self.session.execute(stmt)
            rows = result.all()
            
            stats = {
                row.indicator_name: {
                    "avg_score": float(row.avg_score or 0),
                    "count": row.count
                }
                for row in rows
            }
            
            return stats
        except SQLAlchemyError as e:
            raise RuntimeError("Error calculating indicator averages") from e
