"""
Natural language fraud search endpoint.

POST /api/query/chat - LLM-powered analyst chat (SSE streaming)
"""

import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.chat import stream_analyst_answer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"


@router.post("/chat")
async def analyst_chat(request: QueryRequest) -> StreamingResponse:
    """LLM-powered analyst chat — history managed server-side via session_id."""
    return StreamingResponse(
        stream_analyst_answer(
            request.question,
            session_id=request.session_id,
        ),
        media_type="text/event-stream",
    )
