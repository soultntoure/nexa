"""
Pydantic models for natural language query endpoint.

Contains:
- QueryRequest: question (str)
- QueryResponse: question, answer, sql_executed (nullable),
  data (list[dict], nullable), chart (base64 str, nullable), processed_at
"""
