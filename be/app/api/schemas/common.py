"""
Shared Pydantic models and base schemas.

Contains:
- APIResponse[T]: generic wrapper {"data": T, "correlation_id": str}
- ErrorResponse: {"error": {"code": str, "message": str, "details": dict}}
- PaginationParams: page, page_size
- TimestampMixin: created_at, updated_at fields
"""
