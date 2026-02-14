"""Card lockdown service — flag linked accounts sharing blocked cards."""

import logging
import uuid

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models.alert import Alert
from app.data.db.models.customer import Customer
from app.data.db.models.payment_method import PaymentMethod
from app.data.db.models.withdrawal import Withdrawal
from app.data.db.repositories.payment_method_repository import (
    PaymentMethodRepository,
)

logger = logging.getLogger(__name__)

_LOCKDOWN_REASON = "Card lockdown: shared card with blocked account"


async def check_shared_card(
    session: AsyncSession, external_id: str,
) -> dict:
    """Check if a customer's card is shared with other accounts."""
    customer = await _resolve_customer(session, external_id)
    if not customer:
        return {"shared": False, "linked_count": 0, "linked_accounts": []}

    card = await _get_latest_card(session, customer.id)
    if not card:
        return {"shared": False, "linked_count": 0, "linked_accounts": []}

    repo = PaymentMethodRepository(session)
    linked = await repo.find_linked_by_card(card.id, customer.id)
    linked_accounts = await _fetch_external_accounts(
        session,
        list({pm.customer_id for pm in linked}),
    )
    count = len(linked_accounts)
    return {
        "shared": count > 0,
        "linked_count": count,
        "linked_accounts": linked_accounts,
    }


async def execute_card_lockdown_by_customer(
    session: AsyncSession,
    external_id: str,
    risk_score: float,
) -> dict:
    """
    High-level entry point — resolves customer, finds their latest
    card payment method + withdrawal, then runs the lockdown.
    """
    customer = await _resolve_customer(session, external_id)
    if not customer:
        return _build_result([], 0, error="Customer not found")

    payment_method = await _get_latest_card(session, customer.id)
    if not payment_method:
        return _build_result([], 0, error="No card payment method found")

    withdrawal = await _get_latest_withdrawal(session, customer.id)
    if not withdrawal:
        return _build_result([], 0, error="No withdrawal found")

    return await _execute_lockdown(
        session, customer.id, payment_method,
        withdrawal.id, risk_score,
    )


async def _resolve_customer(
    session: AsyncSession, external_id: str,
) -> Customer | None:
    """Look up customer by external_id."""
    result = await session.execute(
        select(Customer).where(Customer.external_id == external_id)
    )
    return result.scalar_one_or_none()


async def _get_latest_card(
    session: AsyncSession, customer_id: uuid.UUID,
) -> PaymentMethod | None:
    """Get the most recently used card payment method for a customer."""
    result = await session.execute(
        select(PaymentMethod)
        .where(
            PaymentMethod.customer_id == customer_id,
            PaymentMethod.type == "card",
            PaymentMethod.last_four.is_not(None),
        )
        .order_by(desc(PaymentMethod.last_used_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_latest_withdrawal(
    session: AsyncSession, customer_id: uuid.UUID,
) -> Withdrawal | None:
    """Get the most recent withdrawal for a customer."""
    result = await session.execute(
        select(Withdrawal)
        .where(Withdrawal.customer_id == customer_id)
        .order_by(desc(Withdrawal.requested_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _execute_lockdown(
    session: AsyncSession,
    customer_id: uuid.UUID,
    source_method: PaymentMethod,
    withdrawal_id: uuid.UUID,
    risk_score: float,
) -> dict:
    """Run the full lockdown: find linked cards, flag, blacklist, alert."""
    try:
        repo = PaymentMethodRepository(session)
        linked = await repo.find_linked_by_card(
            source_method.id, customer_id,
        )

        methods_by_id: dict[uuid.UUID, PaymentMethod] = {source_method.id: source_method}
        for method in linked:
            methods_by_id[method.id] = method
        methods_to_blacklist = list(methods_by_id.values())

        customer_ids = list({customer_id, *[pm.customer_id for pm in methods_to_blacklist]})

        all_flagged = all(pm.is_blacklisted for pm in methods_to_blacklist)
        if all_flagged:
            affected_accounts = await _fetch_external_accounts(session, customer_ids)
            logger.info("[CardLockdown] Already locked down, skipping")
            return _build_result(affected_accounts, 0)

        affected_accounts = await _flag_customers(session, customer_ids)
        bl_count = await _blacklist_methods(session, methods_to_blacklist)
        await _create_alerts(session, customer_ids, withdrawal_id, risk_score)
        await session.commit()

        logger.info(
            "[CardLockdown] Flagged %d customers, blacklisted %d methods",
            len(customer_ids), bl_count,
        )
        return _build_result(affected_accounts, bl_count)

    except Exception as e:
        await session.rollback()
        logger.exception("[CardLockdown] Failed: %s", e)
        raise RuntimeError("Card lockdown execution failed") from e


async def _flag_customers(
    session: AsyncSession, customer_ids: list[uuid.UUID],
) -> list[dict[str, str]]:
    """Flag customers and return their external_ids."""
    rows = (await session.execute(
        select(Customer).where(Customer.id.in_(customer_ids))
    )).scalars().all()
    affected_accounts = [
        {
            "customer_id": c.external_id,
            "customer_name": c.name,
        }
        for c in rows
    ]
    affected_accounts.sort(key=lambda account: account["customer_id"])

    await session.execute(
        update(Customer).where(Customer.id.in_(customer_ids))
        .values(is_flagged=True, flag_reason=_LOCKDOWN_REASON)
    )
    return affected_accounts


async def _blacklist_methods(
    session: AsyncSession, methods: list[PaymentMethod],
) -> int:
    """Blacklist all matched payment methods in the lockdown set."""
    ids = [pm.id for pm in methods]
    await session.execute(
        update(PaymentMethod).where(PaymentMethod.id.in_(ids))
        .values(is_blacklisted=True)
    )
    return len(ids)


async def _create_alerts(
    session: AsyncSession,
    customer_ids: list[uuid.UUID],
    withdrawal_id: uuid.UUID,
    risk_score: float,
) -> None:
    """Create card_lockdown alerts for each affected customer (skip duplicates)."""
    existing = (await session.execute(
        select(Alert.customer_id).where(
            Alert.alert_type == "card_lockdown",
            Alert.customer_id.in_(customer_ids),
        )
    )).scalars().all()
    already_alerted = set(existing)

    for cid in customer_ids:
        if cid in already_alerted:
            continue
        session.add(Alert(
            withdrawal_id=withdrawal_id,
            customer_id=cid,
            alert_type="card_lockdown",
            risk_score=risk_score,
            top_indicators=["card_errors", "shared_payment_method"],
        ))


def _build_result(
    affected_accounts: list[dict[str, str]],
    blacklisted_methods: int,
    error: str = "",
) -> dict:
    """Format lockdown result."""
    affected_customer_ids = [
        account["customer_id"]
        for account in affected_accounts
    ]

    result: dict = {
        "affected_customers": affected_customer_ids,
        "affected_accounts": affected_accounts,
        "affected_count": len(affected_accounts),
        "blacklisted_methods": blacklisted_methods,
    }
    if error:
        result["error"] = error
    return result


async def _fetch_external_accounts(
    session: AsyncSession,
    customer_ids: list[uuid.UUID],
) -> list[dict]:
    """Return sorted external ID/name/lock-status for customer UUIDs."""
    if not customer_ids:
        return []

    rows = (await session.execute(
        select(Customer.external_id, Customer.name, Customer.is_flagged)
        .where(Customer.id.in_(customer_ids))
    )).all()

    accounts = [
        {
            "customer_id": ext_id,
            "customer_name": name,
            "is_locked": bool(is_flagged),
        }
        for ext_id, name, is_flagged in rows
    ]
    accounts.sort(key=lambda a: a["customer_id"])
    return accounts
