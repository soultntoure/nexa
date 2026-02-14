# Analyst Chat Feature

Real-time streaming fraud query interface with automatic chart visualization.

## Documentation Structure

This folder documents the analyst chat feature from multiple angles:

### Core Concepts
- **streaming_flow.md** — Complete client-to-API-to-client flow with charting
- **sse_event_contract.md** — SSE event types and payload schemas
- **03_chart_generation.md** — Chart type detection and data validation

### Implementation
- **04_backend_architecture.md** — Service layer, singleton pattern, tool orchestration
- **05_charting_pipeline.md** — Chart builder, suitability checking, fallback logic
- **06_frontend_integration.md** — SSE receiver, chart rendering, error handling

### Operations
- **07_performance_benchmarks.md** — Latency breakdown, throughput metrics
- **08_troubleshooting.md** — Common issues, debugging queries, optimization tips

## Quick Links

| Component | File | Language |
|-----------|------|----------|
| Service Layer | `app/services/chat/streaming_service.py` | Python |
| API Route | `app/api/routes/query.py` | Python |
| Chart Tools | `app/services/chat/charting/` | Python |
| Chart Rendering | `app/agentic_system/tools/chart_tool.py` | Python |
| Frontend | `nexa-fe/pages/query.vue` | Vue 3 + TypeScript |

## Key Features

✅ **Real-time SSE Streaming** — Answer tokens stream as they're generated
✅ **Automatic Chart Detection** — Deterministic + LLM-guided visualization
✅ **Schema Introspection** — Prompt injected with actual DB schema
✅ **Server-side History** — Session memory via LangGraph checkpointer
✅ **Error Recovery** — Text fallback if charting fails
✅ **Performance Optimized** — ~3.7s total latency, 100% accuracy

## Performance Profile

| Metric | Value |
|--------|-------|
| Avg TTFT | 2.9s |
| Avg Total | 3.7s |
| Success Rate | 100% |
| Accuracy | 100% (12/12 stress tests) |

See `07_performance_benchmarks.md` for detailed breakdown.
