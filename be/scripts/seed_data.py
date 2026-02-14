"""
Seed 16 test customers + audit patterns into the fraud detection database.

Run: python -m scripts.seed_data
Requires: running Postgres (docker-compose up db)

Seeding strategy:
  APPROVE  (6)  - Clean profiles: Sarah, James, Aisha, Kenji, Emma, Raj
  ESCALATE (4)  - Ambiguous signals: David, Maria, Tom, Yuki
  BLOCK    (11) - Clear fraud: Victor, Sophie, Ahmed+Fatima, Carlos, Nina,
                   Liam, Olga, Dmitri, Priya, Hassan, Elena
  AUDIT    (3)  - Background audit candidates with evidence + text units

All data is deterministic (random.seed(42), uuid5 for IDs).
"""

import asyncio
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.engine import AsyncSessionLocal
from app.data.db.models import WithdrawalDecision

from scripts.seeding import SCENARIO_SEEDERS, TABLES_TO_TRUNCATE
from scripts.seeding.constants import NOW


async def _create_withdrawal_decisions(session: AsyncSession) -> int:
    """Create withdrawal_decisions for all flagged withdrawals."""
    result = await session.execute(
        text("""
            SELECT w.id, w.status, w.amount
            FROM withdrawals w
            LEFT JOIN withdrawal_decisions wd ON wd.withdrawal_id = w.id
            WHERE (w.status IN ('blocked', 'escalated') OR w.is_fraud = TRUE)
              AND wd.id IS NULL
        """)
    )
    flagged = result.fetchall()

    for w_id, status, amount in flagged:
        decision = "blocked" if status == "blocked" else "escalated"
        score = 0.85 if decision == "blocked" else 0.55
        session.add(WithdrawalDecision(
            id=uuid.uuid4(),
            withdrawal_id=w_id,
            decision=decision,
            composite_score=score,
            reasoning=f"Automated decision: {status} withdrawal of ${amount}",
            decided_at=NOW,
            created_at=NOW,
        ))

    return len(flagged)


async def main() -> None:
    async with AsyncSessionLocal() as session:
        # Truncate all tables (reverse FK order)
        for table in TABLES_TO_TRUNCATE:
            await session.execute(text(f"TRUNCATE {table} CASCADE"))
        await session.commit()
        print("Truncated all tables.")

        # Seed each scenario
        for name, seeder in SCENARIO_SEEDERS:
            await seeder(session)
            print(f"  Seeded: {name}")
        await session.commit()

        # Optional posture enrichments for pre-fraud signal demos
        try:
            from scripts.seed_posture_enrichments import seed_posture_enrichments
        except ModuleNotFoundError:
            seed_posture_enrichments = None

        if seed_posture_enrichments is not None:
            enrich_count = await seed_posture_enrichments(session)
            await session.commit()
            print(f"Applied {enrich_count} posture enrichments.")

        # Create withdrawal decisions for flagged withdrawals
        count = await _create_withdrawal_decisions(session)
        await session.commit()
        print(f"Created {count} withdrawal_decisions for flagged withdrawals.")

        # Seed dashboard data (evaluations, indicator results, alerts)
        from scripts.seed_dashboard import seed_dashboard_data

        eval_count = await seed_dashboard_data(session)
        await session.commit()
        print(f"Created {eval_count} evaluations with indicator results and alerts.")

        print(f"\nDone - {len(SCENARIO_SEEDERS)} scenarios seeded.")


if __name__ == "__main__":
    asyncio.run(main())
