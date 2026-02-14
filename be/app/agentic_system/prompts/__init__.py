"""Agent prompts package.

Three agent types:
  - investigators:  3 consolidated investigators (parallel, all 3 always run)
  - triage:         triage verdict synthesizer (final decision after investigators)
  - analyst_chat:   conversational analytics assistant
"""

from app.agentic_system.prompts.investigators import (
    INVESTIGATOR_PROMPTS,
    build_investigator_prompt,
)
from app.agentic_system.prompts.triage import TRIAGE_VERDICT_PROMPT

__all__ = [
    "INVESTIGATOR_PROMPTS",
    "build_investigator_prompt",
    "TRIAGE_VERDICT_PROMPT",
]
