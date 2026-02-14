"""Public utility facade for background-audit candidate generation."""

from app.core.background_audit.candidate_metrics import (
    avg_confidence,
    evidence_quality,
    novelty_to_float,
)
from app.core.background_audit.merge_logic import (
    initialize_dedupe_metadata,
    should_skip_pattern,
)
from app.core.background_audit.pattern_card import (
    extract_agent_fields,
)
from app.core.background_audit.signature_matching import (
    CandidateSignature,
    build_candidate_signature,
    match_duplicate_candidate,
    merge_signatures,
)
from app.services.background_audit.components.internals.candidate_pattern_card_builder import (
    build_pattern_card,
)
from app.services.background_audit.components.internals.candidate_support_metrics import (
    build_evidence_records,
)

__all__ = [
    "CandidateSignature",
    "avg_confidence",
    "build_candidate_signature",
    "build_evidence_records",
    "build_pattern_card",
    "evidence_quality",
    "extract_agent_fields",
    "initialize_dedupe_metadata",
    "match_duplicate_candidate",
    "merge_signatures",
    "novelty_to_float",
    "should_skip_pattern",
]
