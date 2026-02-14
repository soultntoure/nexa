# Fraud Detection System

AI-powered two-pipeline fraud detection for payout requests. The **new pipeline** (investigator) uses rule engine + optional LLM analysis with 0.14s clean cases and 12.1s suspicious cases. The **old pipeline** (evaluate) remains for comparison.

## Documentation Structure

| File | What it covers |
|------|---------------|
| `investigator_pipeline.md` | End-to-end flow: rule engine → triage skip gate → LLM triage → parallel investigators → blended scoring |
| `agentic_system.md` | LLM architecture: triage router, 3 investigator roles, constellation patterns, schemas, design principles |

## Quick Links

| Component | File | Language |
|-----------|------|----------|
| New Pipeline Service | `app/services/fraud/investigator_service.py` | Python |
| Rule Engine Indicators | `app/core/indicators/` | Python |
| Risk Scoring | `app/core/scoring.py` | Python |
| Triage Router Prompt | `app/agentic_system/prompts/triage.py` | Python |
| Investigator Prompts | `app/agentic_system/prompts/investigators/` | Python (3 files) |
| Agent Framework | `app/agentic_system/base_agent.py` | Python |
| Schemas | `app/agentic_system/schemas/triage.py` | Python |
| API Route (New) | `app/api/routes/investigate.py` | Python |
| API Route (Old) | `app/api/routes/payout.py` | Python |

## Key Features

✅ **Rule Engine Skip Gate** — 56% of clean traffic skips LLM (0.14s, 0 calls)
✅ **Constellation Patterns** — Triage reads 8 scores as cross-signal patterns
✅ **Targeted Investigators** — 0-3 LLM agents run in parallel on hypothesis-driven SQL queries
✅ **Blended Scoring** — 60% rule engine + 40% LLM (never downgrades rule decision)
✅ **Structured Output** — All LLM results constrained by Pydantic schemas + token limits
✅ **Error Recovery** — Fallback investigators, persistence isolated from response

## Performance Profile

| Traffic | % | Latency | LLM Calls | Path |
|---------|---|---------|-----------|------|
| Clean (rule only) | 56% | **0.14s** | 0 | Rule engine → skip gate → return |
| Suspicious (LLM analysis) | 44% | **12.1s** | 2-3 | Rule engine → triage → 1-3 investigators |
| Blended (80/20 mix) | 100% | **~2.8s** | — | Real-world traffic pattern |

## Architecture Overview

```
POST /api/payout/investigate
    ↓
Rule Engine (50ms, 8 parallel indicators)
    ↓
Skip Gate: score < 0.30 or >= 0.70?
    ├─→ Yes (56%): Auto-decide, return (0.14s, 0 LLM calls)
    └─→ No: Proceed to Triage
    ↓
Triage Router (1.5s, 1 LLM call)
    Reads 8 scores as constellation → assigns 0-3 investigators
    ↓
Investigators (10-12s, 2-3 parallel LLM calls)
    Financial Behavior, Identity & Access, Cross-Account
    ↓
Blended Scoring (60% rule + 40% LLM)
    ↓
Persist to DB
    ↓
Return InvestigatorResponse
```

## Getting Started

Read the docs in this order:

1. **investigator_pipeline.md** — Understand the end-to-end flow and how triage skip gate works
2. **agentic_system.md** — Learn about triage router, investigator roles, and LLM architecture

For the 8 rule indicators and scoring details, see `investigator_pipeline.md` (Rule Engine section) and [architecture/problem_statement.md](../../architecture/problem_statement.md).
