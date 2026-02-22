# Agentic System

The agentic system is Nexa's AI backbone. It wraps LangChain 1.0 agents powered by **Google Gemini** and provides reusable, composable building blocks for fraud investigation, background auditing, and weight drift analysis.

---

## Component Diagram

```mermaid
graph TD
    subgraph Agentic System
        BA[BaseAgent]
        AC[AgentConfig]
        BAG[BackgroundAuditAgent]
        WDA[WeightDriftAgent]

        subgraph Tools
            SQL[SQL Toolkit<br>sql_db_query]
            RO[ReadOnlySQLMiddleware]
            SB[SchemaBuilder]
            ANALYSIS[Analysis Tools<br>calculate_statistics<br>detect_anomaly<br>calculate_velocity]
            KMEANS[KMeansClusterTool]
            CHART[render_chart]
            WEB[fraud_web_search<br>Tavily]
        end

        subgraph Prompts
            AUDIT_P[background_audit.py]
            DRIFT_P[weight_drift.py]
            TRIAGE_P[triage.py]
            INV_P[investigators/]
            CHAT_P[analyst_chat.py]
        end

        subgraph Schemas
            IND_S[IndicatorResult]
            TRIAGE_S[TriageResult / InvestigatorResult]
            AUDIT_S[AgentSynthesisResult]
        end
    end

    AC -->|configures| BA
    BA -->|builds LLM| GEMINI[(Gemini LLM)]
    BA -->|wraps| AGENT[create_agent]

    BAG -->|owns| BA
    WDA -->|owns| BA

    BA -->|auto-injects| RO
    SQL -->|intercepted by| RO
    SB -->|injects schema into| AUDIT_P
    SB -->|injects schema into| DRIFT_P

    BAG -->|uses prompt| AUDIT_P
    BAG -->|structured output| AUDIT_S
    WDA -->|uses prompt| DRIFT_P
    WDA -->|structured output| AUDIT_S
```

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Composition over inheritance** | Agents own a `BaseAgent`, never subclass it. Keeps specializations shallow and testable. |
| **Frozen `AgentConfig` dataclass** | Immutable config prevents runtime mutation bugs. All tuning happens at construction time. |
| **`ReadOnlySQLMiddleware` as singleton** | SQL safety is a cross-cutting concern injected automatically when any `sql_db_query` tool is present. No per-agent configuration needed. |
| **Schema injection at construction** | Live DB schema (via `schema_builder.py`) is embedded into the prompt string at agent creation — not at call time — keeping per-request latency minimal. |
| **`invoke_verbose` for audit agents** | Background audit and weight drift need a tool trace for the analyst UI. Investigation agents use plain `invoke`. |
| **Fallback dicts on failure** | Every agent returns a fallback result on exception instead of crashing the pipeline. Analysts see a degraded but complete response. |
| **Gemini `gemini-3-flash-preview` default** | Fast, cheap, and sufficient for structured output tasks. `thinking_level="low"` for investigators/triage keeps latency under 25s timeout. |

---

## Files

| File | Role |
|------|------|
| `base_agent.py` | `BaseAgent` + `AgentConfig` — core LangChain wrapper |
| `agents/background_audit_agent.py` | Autonomous fraud pattern synthesizer |
| `agents/weight_drift_agent.py` | Autonomous weight drift investigator |
| `tools/sql/toolkit.py` | `SQLDatabaseToolkit` setup, `FRAUD_DB_TABLES` whitelist |
| `tools/sql/read_only_middleware.py` | Blocks INSERT/UPDATE/DELETE/DROP before execution |
| `tools/sql/schema_builder.py` | Live schema docs + critical notes for LLM prompts |
| `tools/sql/analysis.py` | Statistical `@tool` functions: stats, anomaly, velocity, cohort |
| `tools/kmeans_tool.py` | KMeans on ChromaDB embeddings for cluster comparison |
| `tools/chart_tool.py` | `render_chart` — produces chart spec for the analyst UI |
| `tools/web_search_tool.py` | Tavily fraud typology search (optional, key-guarded) |
| `prompts/background_audit.py` | System prompt for fraud pattern synthesis |
| `prompts/weight_drift.py` | System prompt for weight drift analysis |
| `prompts/triage.py` | System prompt for final verdict synthesis |
| `prompts/investigators/` | Per-investigator prompts (financial, identity, cross-account) |
| `prompts/analyst_chat.py` | System prompt for the analyst chat interface |
| `schemas/indicators.py` | `IndicatorResult` — output schema for all indicator agents |
| `schemas/triage.py` | `TriageResult`, `InvestigatorResult`, `InvestigatorAssignment` |
| `schemas/background_audit.py` | `AgentSynthesisResult`, `WebReference`, `SQLFinding`, `Recommendation` |

---

## Sequence: BackgroundAuditAgent Invocation

```mermaid
sequenceDiagram
    participant F as BackgroundAuditFacade
    participant BAA as BackgroundAuditAgent
    participant BA as BaseAgent
    participant G as Gemini LLM
    participant MW as ReadOnlySQLMiddleware
    participant DB as PostgreSQL

    F->>BAA: synthesize_candidate(evidence_text)
    BAA->>BA: invoke_verbose(evidence_text)
    BA->>G: ainvoke({messages: [user: evidence_text]})
    G-->>BA: tool_call: sql_db_query(SELECT ...)
    BA->>MW: awrap_tool_call(sql_db_query)
    MW->>MW: detect_mutating_sql(query)
    alt query is SELECT
        MW->>DB: execute(SELECT ...)
        DB-->>MW: rows
        MW-->>BA: ToolMessage(rows)
    else mutating keyword found
        MW-->>BA: ToolMessage(BLOCKED)
    end
    BA->>G: feed tool result
    G-->>BA: structured_response: AgentSynthesisResult
    BA-->>BAA: (AgentSynthesisResult, tool_trace)
    BAA-->>F: (result_dict, tool_trace)
```

---

## Sequence: Investigator Pipeline (InvestigatorService)

```mermaid
sequenceDiagram
    participant API as POST /investigate
    participant IS as InvestigatorService
    participant RE as Rule Engine<br>run_all_indicators
    participant INV as Investigators<br>[financial, identity, cross_account]
    participant TV as Triage Verdict<br>BaseAgent
    participant G as Gemini LLM

    API->>IS: investigate(FraudCheckRequest)
    IS->>RE: run_all_indicators(rule_ctx)
    RE-->>IS: list[IndicatorResult]
    IS->>IS: calculate_risk_score(results, weights)
    Note over IS: scoring.decision = approved/escalated/blocked

    alt decision == "approved" (no posture uplift)
        IS->>IS: _build_skip_triage()
        Note over IS: Skip investigators entirely
    else decision requires review
        IS->>INV: _run_investigators (parallel asyncio.gather)
        INV->>G: invoke per investigator
        G-->>INV: InvestigatorResult x3
        INV-->>IS: findings[]
        IS->>TV: _run_triage_verdict(context + findings)
        TV->>G: invoke(TriageResult schema)
        G-->>TV: TriageResult
        TV-->>IS: (TriageResult, elapsed_s)
    end

    IS->>IS: apply_verdict(scoring, triage, posture_uplift)
    IS->>IS: persist_investigation(DB)
    IS-->>API: result dict
```
