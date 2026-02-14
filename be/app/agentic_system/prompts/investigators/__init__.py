"""Investigator prompts — 3 consolidated agents with scoped table access.

Exports:
  - INVESTIGATOR_PROMPTS: dict mapping investigator_name -> prompt string
  - build_investigator_prompt(): builds full prompt with base + specific
"""

from app.agentic_system.prompts.investigators.base import build_investigator_base
from app.agentic_system.prompts.investigators.cross_account import CROSS_ACCOUNT_PROMPT
from app.agentic_system.prompts.investigators.financial_behavior import (
    FINANCIAL_BEHAVIOR_PROMPT,
)
from app.agentic_system.prompts.investigators.identity_access import (
    IDENTITY_ACCESS_PROMPT,
)

INVESTIGATOR_PROMPTS: dict[str, str] = {
    "financial_behavior": FINANCIAL_BEHAVIOR_PROMPT,
    "identity_access": IDENTITY_ACCESS_PROMPT,
    "cross_account": CROSS_ACCOUNT_PROMPT,
}


def build_investigator_prompt(
    investigator_name: str, weight_context: str = "",
) -> str:
    """Concatenate scoped base + specific investigator prompt."""
    base = build_investigator_base(investigator_name, weight_context=weight_context)
    specific = INVESTIGATOR_PROMPTS[investigator_name]
    return base + "\n" + specific


__all__ = [
    "INVESTIGATOR_PROMPTS",
    "build_investigator_prompt",
]
