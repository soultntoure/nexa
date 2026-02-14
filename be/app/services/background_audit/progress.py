"""SSE progress events for background audit pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from pydantic import BaseModel, Field


class SSEEvent(BaseModel):
    """Frontend-friendly SSE event for real-time pipeline progress."""

    type: str = Field(description="phase_start|progress|hypothesis|candidate|agent_tool|insight|complete|error")
    phase: str | None = Field(None, description="extract|embed_cluster|investigate")
    title: str = Field(description="Human-readable heading")
    detail: str | None = Field(None, description="Sub-text for the heading")
    narration: str | None = Field(None, description="Plain-English explanation of what is happening")
    progress: float | None = Field(None, ge=0.0, le=1.0, description="Phase progress 0-1")
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProgressEmitter(Protocol):
    """Protocol for emitting SSE events."""

    async def emit(self, event_type: str, data: dict[str, Any]) -> None: ...


def build_event(
    event_type: str,
    title: str,
    phase: str | None = None,
    detail: str | None = None,
    narration: str | None = None,
    progress: float | None = None,
    **metadata: Any,
) -> SSEEvent:
    """Convenience factory for SSEEvent."""
    return SSEEvent(
        type=event_type,
        phase=phase,
        title=title,
        detail=detail,
        narration=narration,
        progress=progress,
        metadata=metadata,
    )
