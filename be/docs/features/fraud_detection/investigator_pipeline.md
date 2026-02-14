# Investigator Pipeline

End-to-end flow orchestrating rule engine, triage skip gate, optional LLM analysis, and blended scoring.

## End-to-End Pipeline

```mermaid
graph TD
    A["POST /api/payout/investigate"] --> B["build_rule_ctx"]
    B --> C["run_all_indicators<br/>8 parallel SQL queries"]
    C --> D["calculate_risk_score"]
    D --> E["format_indicators_for_llm"]
    E --> F["build_tools"]

    F --> G{score < 0.30<br/>or >= 0.70?}

    G -->|Yes: approved/blocked| H["Skip triage<br/>assignments = empty"]
    G -->|No: gray zone| I["_run_triage<br/>1 LLM call"]

    H --> J["_run_investigators<br/>0-3 parallel agents"]
    I --> J

    J --> K["_compute_decision<br/>blend 60% rule + 40% LLM"]
    K --> L["_build_investigation_data"]
    L --> M["_persist<br/>evaluation + indicators"]
    M --> N["Return response"]

    classDef rule fill:#7ED321,stroke:#333,stroke-width:2px,color:#000
    classDef llm fill:#F5A623,stroke:#333,stroke-width:2px,color:#000
    classDef gate fill:#4A90E2,stroke:#333,stroke-width:2px,color:#000
    classDef persist fill:#9B59B6,stroke:#333,stroke-width:2px,color:#fff

    class C,D rule
    class I,J llm
    class G,K gate
    class L,M persist
```

Entry point: `app/services/fraud/investigator_service.py:76`

## Rule Engine (50ms)

Eight SQL-based indicators run in parallel to compute composite risk score.

### Parallel Indicators

```mermaid
graph LR
    CTX["rule_ctx"] --> G["asyncio.gather"]
    G --> I1["amount_anomaly"]
    G --> I2["velocity"]
    G --> I3["payment_method"]
    G --> I4["geographic"]
    G --> I5["device_fingerprint"]
    G --> I6["trading_behavior"]
    G --> I7["recipient"]
    G --> I8["card_errors"]

    I1 --> R["list of IndicatorResult"]
    I2 --> R
    I3 --> R
    I4 --> R
    I5 --> R
    I6 --> R
    I7 --> R
    I8 --> R

    classDef ind fill:#7ED321,stroke:#333,stroke-width:2px,color:#000
    class I1,I2,I3,I4,I5,I6,I7,I8 ind
```

### Indicator Weights

| Indicator | Weight | Why |
|-----------|--------|-----|
| trading_behavior | 1.5 | Deposit & run = #1 fraud pattern |
| device_fingerprint | 1.3 | Cross-account device sharing |
| geographic | 1.2 | Impossible travel, VPN mismatches |
| card_errors | 1.2 | Card testing patterns |
| amount_anomaly | 1.0 | Baseline |
| velocity | 1.0 | Baseline |
| payment_method | 1.0 | Baseline |
| recipient | 1.0 | Baseline |

### Scoring Formula

```
composite = Σ(score × weight) / Σ(weight)
```

**Override rules**:
- Any 1 indicator ≥ 0.7 + confidence ≥ 0.8 → force `escalated`
- 4+ indicators ≥ 0.6 + confidence ≥ 0.8 → force `blocked`

**Performance**: ~50ms for all 8 indicators.

## Triage Skip Gate

The single most impactful optimization: skips all LLM calls for obvious cases.

### Branch Decision

```mermaid
flowchart TD
    A["Calculate<br/>composite_score"] --> B{score < 0.30<br/>or >= 0.70?}

    B -->|Yes| C["Decision:<br/>approved OR blocked"]
    B -->|No| D["Decision:<br/>escalated<br/>Gray zone"]

    C --> E["assignments = empty<br/>0 LLM calls"]
    D --> F["Run triage router<br/>1 LLM call"]

    E --> G["Investigators skipped"]
    F --> H["Assign 0-3<br/>investigators"]

    classDef approved fill:#7ED321,stroke:#333,stroke-width:2px,color:#000
    classDef escalated fill:#F5A623,stroke:#333,stroke-width:2px,color:#000
    classDef blocked fill:#E74C3C,stroke:#333,stroke-width:2px,color:#fff
    classDef gate fill:#4A90E2,stroke:#333,stroke-width:2px,color:#000

    class C approved
    class D escalated
    class B gate
```

**Impact**: 56% of traffic (clean cases) skips to response in **0.14s** with 0 LLM calls.

## Triage Router (1.5s)

Reads 8 rule engine scores as a "constellation" pattern and assigns 0-3 targeted investigators.

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Service as InvestigatorService
    participant Agent as BaseAgent
    participant Gemini as Gemini 3-Flash

    Service->>Agent: TriageConfig(prompt=TRIAGE_ROUTER_PROMPT, output_schema=TriageResult)
    Agent->>Gemini: 8 indicator scores + request context
    Gemini-->>Agent: TriageResult JSON
    Agent-->>Service: assignments[] (0-3 investigators)

    Note over Service: On LLM error:<br/>fallback to financial_behavior + identity_access
```

### Triage Configuration

| Parameter | Value |
|-----------|-------|
| Model | `gemini-3-flash-preview` |
| Thinking | `low` |
| Max tokens | 512 |
| Tools | None |
| Timeout | 25s |

### Constellation Patterns

| Pattern | Rule Signals | Assigns | Type |
|---------|-------------|---------|------|
| **All clean** | All ≈ 0 | 0 | None |
| **Isolated anomaly** | 1 high, rest clean | 0-1 | Benign |
| **New everything** | New account + device + payment + low trading | financial_behavior + cross_account | Mule |
| **Deposit & Run** | Low trading + high amount | financial_behavior | No-trade withdrawal |
| **Account Takeover** | New device + IP + established account | identity_access | Hijack |
| **Shared infrastructure** | Shared device/IP signals | cross_account | Fraud ring |

## Investigator Dispatch (10-12s)

0-3 investigators run in parallel, each with hypothesis-driven SQL access.

### Parallel Execution

```mermaid
flowchart TD
    A["triage.assignments"] --> B{Empty?}
    B -->|Yes| C["Skip<br/>no investigators"]
    B -->|No| D["asyncio.gather"]
    D --> E1["financial_behavior<br/>~1-2 queries"]
    D --> E2["identity_access<br/>~1-2 queries"]
    D --> E3["cross_account<br/>~1-2 queries"]
    E1 --> F["findings list<br/>0-3 results"]
    E2 --> F
    E3 --> F

    classDef agent fill:#BD10E0,stroke:#333,stroke-width:2px,color:#fff
    classDef gate fill:#4A90E2,stroke:#333,stroke-width:2px,color:#000
    class E1,E2,E3 agent
    class B gate
```

### Investigator Configuration

| Parameter | Value |
|-----------|-------|
| Model | `gemini-3-flash-preview` |
| Thinking | `low` |
| Max tokens | 512 |
| Max iterations | 2 |
| Tools | sql_db_query only |
| Timeout | 25s |
| Prompt enrichment | constellation + rule scores |

### Investigator Roles

| Name | Prompt | Detects | Tables |
|------|--------|---------|--------|
| **financial_behavior** | `prompts/investigators/financial_behavior.py` | Deposit & run, bonus abuse, structuring | customers, transactions, trades, withdrawals, payment_methods |
| **identity_access** | `prompts/investigators/identity_access.py` | Account takeover, impossible travel, session hijacking | customers, devices, ip_history, withdrawals |
| **cross_account** | `prompts/investigators/cross_account.py` | Fraud rings, money mules, shared infrastructure | customers, devices, ip_history, withdrawals, payment_methods |

**Performance**: ~8-12s per investigator (run in parallel).

## Blended Scoring

Combines rule engine decision with investigator findings via weighted average.

### Decision Logic

```mermaid
flowchart TD
    A["No findings?"] -->|Yes| B["Use rule<br/>engine only"]
    A -->|No| C["inv_score = weighted avg<br/>of investigator scores"]
    C --> D["blended = rule*0.6<br/>+ inv*0.4"]
    D --> E{blended >= 0.70<br/>OR high-conf risk?}
    E -->|Yes| F["BLOCKED"]
    E -->|No| G{blended >= 0.30?}
    G -->|Yes| H["ESCALATED"]
    G -->|No| I{rule engine<br/>escalated/blocked?}
    I -->|Yes| J["Keep rule<br/>decision"]
    I -->|No| K["APPROVED"]

    classDef blocked fill:#E74C3C,stroke:#333,stroke-width:2px,color:#fff
    classDef escalated fill:#F5A623,stroke:#333,stroke-width:2px,color:#000
    classDef approved fill:#7ED321,stroke:#333,stroke-width:2px,color:#000
    classDef gate fill:#4A90E2,stroke:#333,stroke-width:2px,color:#000

    class F blocked
    class H,J escalated
    class K approved
    class E,G,I gate
```

**Key rule**: Never downgrade rule engine decision. If rule engine says `blocked` but blended says `approved`, keep `blocked`.

## Persistence

### Investigation Data Structure

Saved to `evaluations.investigation_data` JSONB:

```json
{
  "triage": {
    "constellation_analysis": "string",
    "assignments": [{"investigator": "string", "priority": "string"}],
    "elapsed_s": 3.2
  },
  "investigators": [
    {
      "name": "financial_behavior",
      "score": 0.88,
      "confidence": 0.95,
      "reasoning": "string (max 300 chars)",
      "elapsed_s": 3.1
    }
  ]
}
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Service as InvestigatorService
    participant Eval as evaluations table
    participant Ind as indicator_results table

    Service->>Service: _build_investigation_data(triage, findings)
    Service->>Eval: INSERT evaluation (composite_score, decision, investigation_data)
    Service->>Ind: INSERT 8 indicator_result rows
    Service->>Service: Return response dict

    Note over Service: Errors caught, logged,<br/>do not block response
```

## Error Recovery

| Failure | Location | Fallback |
|---------|----------|----------|
| **Triage LLM error** | line 152-173 | Assign financial_behavior + identity_access at medium priority |
| **Investigator error** | line 239-251 | Exclude from blending; others proceed |
| **All investigators fail** | line 314-322 | Use rule engine decision only |
| **Persistence error** | line 304-305 | Log and continue (don't block response) |

## Performance Breakdown

### By Traffic Type

| Type | % | Latency | LLM Calls | Path |
|------|---|---------|-----------|------|
| Clean | 56% | **0.14s** | 0 | Rule → skip gate → return |
| Suspicious | 44% | **12.1s** | 2-3 | Rule → triage → investigators → blend |
| Blended (80/20) | — | **~2.8s** | — | Mixed path |

### Suspicious Case Breakdown

| Stage | Latency | LLM Calls |
|-------|---------|-----------|
| Rule engine (lines 80-83) | ~50ms | 0 |
| Triage (line 95) | ~1.5s | 1 |
| Investigators (line 97) | ~10-12s | 2 |
| Decision + persist (lines 101-111) | ~50ms | 0 |
| **Total** | **~12.1s** | **3** |

See `scripts/CLAUDE.md` for full 16-customer benchmark table.

## Configuration

### Model Parameters

| Parameter | Triage | Investigators |
|-----------|--------|---------------|
| Model | gemini-3-flash-preview | gemini-3-flash-preview |
| Thinking | low | low |
| Max tokens | 512 | 512 |
| Max iterations | — | 2 |
| Tools | None | sql_db_query |
| Timeout | 25s | 25s |

### Thresholds

| Threshold | Value | Effect |
|-----------|-------|--------|
| APPROVE | score < 0.30 | Auto-approve, skip triage |
| ESCALATE | 0.30 ≤ score < 0.70 | Gray zone, run triage |
| BLOCK | score ≥ 0.70 | Auto-block, skip triage |
| Blending | 60/40 | Rule engine / investigators |

**File**: `app/core/scoring.py` and `app/services/fraud/investigator_service.py:29-32`

## Key Files

| Layer | File | Role |
|-------|------|------|
| Service | `app/services/fraud/investigator_service.py` | Pipeline orchestrator |
| Indicators | `app/core/indicators/__init__.py` | Rule engine runner (asyncio.gather) |
| Scoring | `app/core/scoring.py` | Risk score calculation |
| Triage | `app/agentic_system/prompts/triage.py` | Constellation analysis prompt |
| Investigators | `app/agentic_system/prompts/investigators/*.py` | 3 investigator prompts |
| Agent | `app/agentic_system/base_agent.py` | LangChain + Gemini wrapper |
| Schemas | `app/agentic_system/schemas/triage.py` | TriageResult, InvestigatorResult |
| Tools | `app/services/fraud/internals/tools.py` | SQL tool factory |
| Persistence | `app/services/fraud/internals/persistence.py` | Build DB models for save |
