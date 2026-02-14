# Background Audit Pipeline — Feature Documentation

## Overview

Discovers fraud patterns by extracting reasoning from confirmed-fraud investigations, embedding into vectors, clustering similar reasoning, and surfacing candidate patterns for admin review.

**Current state**: Async pipeline with parallel cluster investigation (Stage 2). Phase 3 investigates multiple clusters concurrently via `asyncio.gather()` with a Semaphore(4) to batch clusters into 2 waves (~35s total vs ~3min sequential). Named clusters show their source types and preview text in hypothesis events. Evidence is joined from the `audit_candidate_evidence` database table. Artifact writing is non-blocking—fires as a background task without delaying the `complete` event.

## Documents (read in pipeline execution order)

| # | File | Phase | What You'll Learn |
|---|------|-------|-------------------|
| 1 | [trigger_and_facade.md](./trigger_and_facade.md) | Entry | API trigger, facade orchestration, run lifecycle |
| 2 | [extract_phase.md](./extract_phase.md) | Phase 1 | Cohort query, text normalization, PII masking, dedup |
| 3 | [embed_and_cluster.md](./embed_and_cluster.md) | Phase 2 | Gemini embeddings, HDBSCAN clustering, novelty detection |
| 4 | [candidates_and_artifacts.md](./candidates_and_artifacts.md) | Phase 3–4 | Quality gates, agent synthesis, evidence ranking, file output |
| 5 | [scoring_and_clustering.md](./scoring_and_clustering.md) | Reference | All formulas: quality score, ranking, novelty thresholds, text processing |
| 6 | [api_and_data.md](./api_and_data.md) | Reference | Endpoints, DB models, JSONB schemas |
| 7 | [next_up.md](./next_up.md) | Future | Web search tool, streaming, dashboard integration |
