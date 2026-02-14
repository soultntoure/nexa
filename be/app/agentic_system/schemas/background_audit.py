"""Schemas for background audit agent outputs."""

from pydantic import BaseModel, Field


class WebReference(BaseModel):
    """A web source corroborating or describing a fraud pattern."""

    url: str = Field(description="Source URL")
    title: str = Field(description="Page title or description")
    relevance: str = Field(description="How this source relates to the finding")


class SQLFinding(BaseModel):
    """A SQL-derived insight from the fraud database."""

    query_summary: str = Field(description="the query formatted as a plain language question")
    result_summary: str = Field(description="Key finding from the query")


class Recommendation(BaseModel):
    """A specific actionable recommendation for addressing a finding."""

    action: str = Field(description="What to do, e.g. 'Pin indicator' or 'Reset customer weights'")
    target: str = Field(description="Which indicator or customer this applies to")
    reason: str = Field(description="Why this action is recommended")
    priority: str = Field(default="medium", description="'high', 'medium', or 'low'")


class AgentSynthesisResult(BaseModel):
    """Structured output from the background audit synthesis agent."""

    plain_language: str = Field(description="Admin-facing narrative of the pattern")
    analyst_notes: str = Field(description="Technical notes for fraud analysts")
    limitations: str = Field(description="Known limitations of this finding")
    uncertainty: str = Field(description="Areas of uncertainty")
    formal_pattern_name: str = Field(
        default="Unknown",
        description="Recognized fraud typology name (e.g. 'Account Takeover', 'Smurfing')",
    )
    recommendations: list[Recommendation] = Field(
        default_factory=list,
        description="Actionable recommendations for addressing drift issues",
    )
    web_references: list[WebReference] = Field(
        default_factory=list,
        description="Web sources corroborating this pattern",
    )
    clustering_notes: str = Field(
        default="",
        description="Notes on cluster quality or KMeans comparison results",
    )
    sql_findings: list[SQLFinding] = Field(
        default_factory=list,
        description="Insights from SQL deep-dive queries",
    )
