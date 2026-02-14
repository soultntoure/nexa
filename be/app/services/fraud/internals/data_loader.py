"""Load customer profiles, posture, and pattern matches from DB."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import joinedload

from app.data.db.models.customer_risk_posture import CustomerRiskPosture
from app.data.db.models.customer_weight_profile import CustomerWeightProfile
from app.data.db.repositories.weight_profile_repository import WeightProfileRepository
from app.services.prefraud.posture_service import PostureService

logger = logging.getLogger(__name__)


class InvestigatorDataLoader:
    """Async data loader for investigator pipeline DB queries."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def load_customer_profile(
        self, external_id: str,
    ) -> CustomerWeightProfile | None:
        """Load active weight profile by customer external_id."""
        from app.data.db.models.customer import Customer

        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(Customer.id).where(Customer.external_id == external_id),
                )
                customer_uuid = result.scalar_one_or_none()
                if customer_uuid is None:
                    return None
                repo = WeightProfileRepository(session)
                return await repo.get_active(customer_uuid)
        except Exception:
            logger.warning("Failed to load weight profile for %s", external_id)
            return None

    async def load_posture(
        self, external_id: str,
    ) -> CustomerRiskPosture | None:
        """Load current risk posture by customer external_id.

        Resolves external_id -> UUID, then delegates to PostureService.
        """
        from app.data.db.models.customer import Customer

        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(Customer.id).where(Customer.external_id == external_id),
                )
                customer_uuid = result.scalar_one_or_none()
                if customer_uuid is None:
                    return None

            posture_svc = PostureService(self._session_factory)
            return await posture_svc.get_current(customer_uuid)
        except Exception:
            logger.warning("Failed to load posture for %s", external_id)
            return None

    async def load_pattern_matches(self, external_id: str) -> list:
        """Load active pattern matches by customer external_id.

        Resolves external_id -> UUID, then queries PatternMatch rows
        joined with active FraudPattern.
        """
        from app.data.db.models.customer import Customer
        from app.data.db.models.fraud_pattern import FraudPattern
        from app.data.db.models.pattern_match import PatternMatch

        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(Customer.id).where(Customer.external_id == external_id),
                )
                customer_uuid = result.scalar_one_or_none()
                if customer_uuid is None:
                    return []

                result = await session.execute(
                    select(PatternMatch)
                    .join(FraudPattern)
                    .where(
                        PatternMatch.customer_id == customer_uuid,
                        PatternMatch.is_current == True,
                        FraudPattern.state == "active",
                    )
                    .options(joinedload(PatternMatch.pattern))
                )
                matches = list(result.scalars().all())
                for m in matches:
                    session.expunge(m)
                return matches
        except Exception:
            logger.warning("Failed to load pattern matches for %s", external_id)
            return []
