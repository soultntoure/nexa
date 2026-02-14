"""Geographic Risk indicator — IP/VPN/country mismatch detection."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agentic_system.schemas.indicators import IndicatorResult
from app.core.indicators.base import BaseIndicator
from app.data.db.repositories.ip_history_repository import IPHistoryRepository


class GeographicIndicator(BaseIndicator):
    name = "geographic"
    weight = 1.0

    async def evaluate(
        self, ctx: dict, session: AsyncSession,
    ) -> IndicatorResult:
        repo = IPHistoryRepository(session)
        rows = await repo.get_recent_with_country(ctx["customer_id"])
        distinct_7d = await repo.get_distinct_countries_7d(ctx["customer_id"])
        historical_countries = await repo.get_distinct_countries_all_time(ctx["customer_id"])
        score, reasoning, evidence = _compute_score(
            rows, ctx, distinct_7d, historical_countries,
        )
        return IndicatorResult(
            indicator_name="geographic",
            score=score,
            confidence=1.0,
            reasoning=reasoning,
            evidence=evidence,
        )


def _compute_score(
    rows: list, ctx: dict, distinct_7d: int, historical_countries: int = 1,
) -> tuple[float, str, dict]:
    """Score based on VPN, country mismatch, and IP diversity.

    Scores are dampened proportionally to the customer's historical
    country footprint — established travelers are penalized less.
    """
    if not rows:
        return 0.2, "No IP connection history is available for this customer.", {"distinct_7d": 0}

    latest = rows[0]
    is_vpn = bool(latest["is_vpn"])
    home = (ctx.get("customer_country") or "").upper()
    current_loc = str(latest["location"] or "")
    current_country = current_loc.split(", ")[-1].strip().upper() if current_loc else ""
    country_match = home == current_country if home and current_country else True

    # Dampen factor: 1.0 for single-country users, down to 0.3 for 5+ countries
    dampen = _traveler_dampen_factor(historical_countries)

    evidence = {
        "is_vpn": is_vpn,
        "country_match": country_match,
        "distinct_countries_7d": distinct_7d,
        "historical_countries": historical_countries,
        "dampen_factor": round(dampen, 2),
        "current_location": current_loc,
        "home_country": home,
    }

    score = 0.0

    if is_vpn:
        score += 0.05
    if not country_match:
        score += 0.15 * dampen
    if distinct_7d >= 4:
        score += 0.20 * dampen
    elif distinct_7d >= 2:
        score += 0.05 * dampen

    score = min(score, 1.0)
    from app.core.indicators._reasoning import build_geographic_reasoning
    return round(score, 2), build_geographic_reasoning(evidence, round(score, 2)), evidence


def _traveler_dampen_factor(historical_countries: int) -> float:
    """Return a multiplier [0.3, 1.0] based on how many countries the user has historically connected from.

    1 country  → 1.0  (single-location user, full penalty)
    2 countries → 0.7
    3 countries → 0.5
    4 countries → 0.4
    5+ countries → 0.3 (established traveler, minimal penalty)
    """
    if historical_countries <= 1:
        return 1.0
    if historical_countries == 2:
        return 0.7
    if historical_countries == 3:
        return 0.5
    if historical_countries == 4:
        return 0.4
    return 0.3
