# Deriv Fraud Detection System

AI-powered payment fraud detection for the Deriv trading platform. Every withdrawal passes through 8 parallel rule indicators; ambiguous cases escalate to LLM-powered investigators where officers make final decisions.

---

## System Architecture

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        UI[Web Dashboard]
        API[API Consumer]
    end

    subgraph API["API Layer"]
        Routes[FastAPI Routes]
        Validators[Pydantic Validators]
    end

    subgraph Services["Service Layer"]
        Fraud[Fraud Detection]
        Chat[Analyst Chat]
        Control[Officer Control]
        Dashboard[Dashboard]
    end

    subgraph Core["Core Layer"]
        Scoring[Scoring Engine]
        Indicators[8 Indicators]
        Calibration[Calibration]
    end

    subgraph Agents["Agentic Layer"]
        Triage[Triage Router]
        Inv1[Financial Investigator]
        Inv2[Identity Investigator]
        Inv3[Cross-Account Investigator]
    end

    subgraph Data["Data Layer"]
        PG[(PostgreSQL)]
        Chroma[(ChromaDB)]
    end

    UI --> Routes
    API --> Routes
    Routes --> Validators
    Validators --> Fraud
    Validators --> Chat
    Validators --> Control
    Validators --> Dashboard

    Fraud --> Scoring
    Fraud --> Triage
    Fraud --> Inv1
    Fraud --> Inv2
    Fraud --> Inv3

    Scoring --> Indicators
    Calibration --> Scoring

    Indicators --> PG
    Triage --> PG
    Inv1 --> PG
    Inv2 --> PG
    Inv3 --> PG

    style UI fill:#ffffff,stroke:#0d47a1,stroke-width:2px,color:#000
    style API fill:#ffffff,stroke:#1b5e20,stroke-width:2px,color:#000
    style Services fill:#ffffff,stroke:#e65100,stroke-width:2px,color:#000
    style Core fill:#ffffff,stroke:#880e4f,stroke-width:2px,color:#000
    style Agents fill:#ffffff,stroke:#4a148c,stroke-width:2px,color:#000
    style Data fill:#ffffff,stroke:#006064,stroke-width:2px,color:#000
    style Routes fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Validators fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Fraud fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Chat fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Control fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Dashboard fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Scoring fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Indicators fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Calibration fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Triage fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Inv1 fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Inv2 fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Inv3 fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style PG fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Chroma fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
```

---

## Fraud Detection Pipeline

```mermaid
flowchart LR
    subgraph Input
        W[Withdrawal Request]
    end

    subgraph Rules["Rule Engine<br/>(~50ms)"]
        I1[Amount Anomaly]
        I2[Velocity]
        I3[Geographic]
        I4[Device]
        I5[Trading]
        I6[Recipient]
        I7[Payment]
        I8[Card Errors]
    end

    subgraph Score["Scoring"]
        SC[Weighted Composite]
        TH[Thresholds]
    end

    subgraph Decision["Decision"]
        A[Approve]
        E[Escalate]
        B[Block]
    end

    subgraph LLM["LLM Investigation<br/>(~12s)"]
        T[Triage]
        Inv[Investigators]
        V[Verdict]
    end

    subgraph Officer["Officer Queue"]
        Q[Review Queue]
        D[Decision]
    end

    W --> I1 & I2 & I3 & I4 & I5 & I6 & I7 & I8
    I1 & I2 & I3 & I4 & I5 & I6 & I7 & I8 --> SC
    SC --> TH
    TH -->|"< 0.30"| A
    TH -->|">= 0.70"| B
    TH -->|"0.30-0.70"| E
    E --> T
    T --> Inv
    Inv --> V
    V --> Q
    Q --> D

    style Input fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Rules fill:#e3f2fd,stroke:#0d47a1,stroke-width:2px,color:#000
    style Score fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
    style Decision fill:#c8e6c9,stroke:#1b5e20,stroke-width:2px,color:#000
    style LLM fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#000
    style Officer fill:#fce4ec,stroke:#880e4f,stroke-width:2px,color:#000
    style W fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style I1 fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style I2 fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style I3 fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style I4 fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style I5 fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style I6 fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style I7 fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style I8 fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style SC fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style TH fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style A fill:#c8e6c9,stroke:#1b5e20,stroke-width:1px,color:#000
    style E fill:#fff9c4,stroke:#f57f17,stroke-width:1px,color:#000
    style B fill:#ffcdd2,stroke:#b71c1c,stroke-width:1px,color:#000
    style T fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Inv fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style V fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style Q fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
    style D fill:#ffffff,stroke:#333,stroke-width:1px,color:#000
```

---

## 8 Parallel Rule Indicators

The rule engine executes 8 independent SQL-based fraud indicators in parallel (~50ms total). Each indicator returns a deterministic risk score (0.0–1.0) with evidence and reasoning.

### Indicator Weights

Higher weight = stronger influence on final decision:

| Indicator | Weight | Rationale |
|----------|--------|------------|
| `trading_behavior` | **1.5** | Highest — deposit-and-run is strongest fraud signal on a trading platform |
| `device_fingerprint` | **1.3** | Cross-account sharing indicates organized fraud/mule networks |
| `card_errors` | **1.2** | Card testing pattern (classic fraud) |
| `amount_anomaly` | 1.0 | Statistical outlier detection |
| `velocity` | 1.0 | Rapid fund extraction detection |
| `geographic` | 1.0 | VPN + country mismatch + travel velocity |
| `payment_method` | 1.0 | Method age + verification + blacklist |
| `recipient` | 1.0 | Name mismatch + cross-account usage |

---

### 1. Amount Anomaly (`amount_anomaly.py`)

Statistical outlier detection using Z-score vs customer's historical withdrawal average.

| Condition | Score | Why |
|-----------|-------|-----|
| No history | 0.30 | Can't assess, moderate caution |
| z ≤ 1.0 (within 1σ) | 0.00 | Normal range |
| z ≤ 2.0 (1–2σ) | 0.25 | Slightly elevated |
| z ≤ 3.0 (2–3σ) | 0.40 | Unusual, <2.3% probability |
| z > 3.0 | min(0.75, 0.40 + (z-3)×0.08) | Extreme outlier, scales with cap |

---

### 2. Velocity (`velocity.py`)

Detects rapid fund extraction by comparing withdrawal counts in time windows against customer baseline.

**Two-stage scoring**:

| Stage | Condition | Score |
|-------|-----------|-------|
| Warn | 1h≥4, 24h≥7, or 7d≥12 | 0.25 |
| Warn + spike | Warn + 2.5x baseline | 0.40 |
| Critical | 1h≥6, 24h≥10, or 7d≥18 | 0.50 |
| Critical + 4x spike | Critical + 4x+ baseline | 0.65 |

**Key insight**: Capped at 0.65 to stay in review zone unless corroborated.

---

### 3. Geographic (`geographic.py`)

Location signals with **travel history dampening** to avoid penalizing legitimate travelers.

| Signal | Base Score | Dampened? |
|--------|-----------|-----------|
| VPN detected | +0.05 | No |
| Country mismatch (IP vs registered) | +0.15 | Yes |
| ≥4 distinct countries in 7d | +0.20 | Yes |
| ≥2 distinct countries in 7d | +0.05 | Yes |

**Dampening factor**: Based on historical distinct countries (1→1.0, 2→0.7, 3→0.5, 4→0.4, 5+→0.3)

---

### 4. Device Fingerprint (`device_fingerprint.py`)

Device trust and cross-account sharing detection.

| Signal | Score |
|--------|-------|
| Shared across ≥3 accounts | +0.70 |
| Shared across 2 accounts | +0.40 |
| Device not trusted | +0.25 |
| Age < 1 day (brand new) | +0.25 |
| Age < 7 days (recent) | +0.15 |

**Weight: 1.3** — Highest after trading_behavior. Cross-account device sharing is the strongest organized fraud signal.

---

### 5. Trading Behavior (`trading_behavior.py`)

Detects "deposit and run" — depositing without trading before withdrawing.

| Signal | Score |
|--------|-------|
| Zero trades | +0.60 |
| < 3 trades | +0.35 |
| < 5 trades | +0.15 |
| Withdrawal/deposit ratio ≥ 0.9 | +0.40 |
| Withdrawal/deposit ratio ≥ 0.7 | +0.25 |

**Weight: 1.5** (highest) — On a **derivatives trading platform**, no trading activity with large withdrawals is the strongest fraud pattern.

---

### 6. Recipient (`recipient.py`)

Recipient trust and cross-account patterns.

| Signal | Score |
|--------|-------|
| Name mismatch (customer ≠ recipient) | +0.30 |
| Recipient used by ≥3 accounts | +0.40 |
| Recipient used by 2 accounts | +0.20 |
| First-time recipient | +0.20 |

---

### 7. Payment Method (`payment_method.py`)

Payment method trustworthiness and churn.

| Signal | Score |
|--------|-------|
| Blacklisted | +0.50 |
| Not verified | +0.20 |
| Age < 7 days | +0.30 |
| Age < 30 days | +0.10 |
| ≥3 methods added in 30d | +0.20 |

---

### 8. Card Errors (`card_errors.py`)

Payment failures and method switching (card testing detection).

| Signal | Score |
|--------|-------|
| ≥5 failed transactions in 30d | +0.50 |
| ≥2 failed transactions in 30d | +0.20 |
| ≥4 distinct methods in 30d | +0.40 |
| ≥3 distinct methods in 30d | +0.20 |

---

## Scoring Thresholds

| Threshold | Value | Effect |
|-----------|-------|--------|
| `APPROVE_THRESHOLD` | 0.30 | Composite score < 0.30 → auto-approve (skip triage) |
| `BLOCK_THRESHOLD` | 0.70 | Composite score >= 0.70 → auto-block (skip triage) |
| `HARD_ESCALATION` | 0.80 | Any single indicator >= 0.80 → force escalation |
| `MULTI_CRITICAL` | 4×0.60 | 4+ indicators >= 0.60 → force block |

---

## Triage & Investigator Flow

```mermaid
sequenceDiagram
    participant Svc as InvestigatorService
    participant Rules as Rule Engine
    participant Triage as Triage Router
    participant Inv1 as Financial Agent
    participant Inv2 as Identity Agent
    participant Inv3 as Cross-Account Agent
    participant Verdict as Verdict Synthesis

    Svc->>Rules: Run 8 indicators
    Rules-->>Svc: Indicator results

    Svc->>Svc: Calculate composite score
    alt Score < 0.30 or >= 0.70
        Svc->>Svc: Skip triage (auto-decide)
    else 0.30-0.70 (gray zone)
        Svc->>Triage: Analyze indicator constellation
        Triage-->>Svc: 0-3 investigator assignments

        par Investigators
            Svc->>Inv1: Run financial_behavior
            Svc->>Inv2: Run identity_access  
            Svc->>Inv3: Run cross_account
        end

        Inv1-->>Svc: Findings + score
        Inv2-->>Svc: Findings + score
        Inv3-->>Svc: Findings + score

        Svc->>Verdict: Blend rule + investigators
    end

    Svc->>Svc: Apply guardrails
    Svc->>Svc: Final decision
```

---

## Analyst Chat Flow

Natural language fraud analytics with SQL generation and optional chart visualization.

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Agent as LangChain Agent
    participant LLM as Gemini
    participant DB as PostgreSQL
    participant Chart as Chart Tool

    Client->>API: "Show fraud trends by country"
    API->>Agent: Stream question
    Agent->>LLM: Generate SQL query
    LLM-->>Agent: SQL
    Agent->>DB: Execute SQL
    DB-->>Agent: Results
    Agent->>LLM: Analyze data for visualization
    LLM-->>Agent: "Good for bar chart"
    Agent->>Chart: render_chart(title, type, x_key, series, rows)
    Chart-->>Agent: Confirmation
    Agent->>Client: SSE token stream + chart JSON
```

**Tools Available to Agent:**
1. **SQL Execution** — Generate and run SQL queries against PostgreSQL
2. **Chart Renderer** — Create bar, line, or pie charts from query results

**Chart Tool** (`app/agentic_system/tools/chart_tool.py`):
- `title`: Chart title (max 60 chars)
- `chart_type`: "bar", "line", or "pie"
- `x_key`: Column for x-axis labels
- `series`: List of metrics for y-axis
- `rows`: Query result data

The agent decides when visualization adds value and calls `render_chart()` automatically after SQL results.

---

## Card Lockdown (Fraud Ring Detection)

```mermaid
flowchart TB
    subgraph Trigger["Trigger"]
        E[Evaluation Blocked]
        C[Card Payment Method]
    end

    subgraph Detect["Detection"]
        P[Find Linked Accounts]
        L[Analyze Pattern]
    end

    subgraph Action["Lockdown Actions"]
        F[Flag Customers]
        B[Blacklist Methods]
        A[Create Alerts]
    end

    E & C --> P
    P --> L
    L --> F
    L --> B
    L --> A
```

---

## Features

| Feature | Description |
|---------|-------------|
| **Dual Pipelines** | Rule engine + optional LLM investigators |
| **8 Indicators** | Parallel SQL-based fraud signals |
| **Triage Router** | LLM assigns targeted investigators |
| **3 Investigators** | Financial behavior, identity access, cross-account |
| **Blended Scoring** | 50% rule + 50% investigator consensus |
| **Analyst Chat** | Natural language queries via SSE |
| **Card Lockdown** | Fraud ring detection |
| **Adaptive Weights** | Per-customer calibration from feedback |

---

## Performance

| Traffic Type | Latency | LLM Calls |
|-------------|---------|-----------|
| Clean (56%) | **0.14s** | 0 |
| Suspicious (44%) | **12.1s** | 2-3 |
| Blended | **~2.8s** | — |

---

## Quick Start

```bash
# Start infrastructure
docker compose up -d

# Seed test data
python -m scripts.seed_data

# Run benchmark
python scripts/benchmark_investigate.py
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/withdrawals/investigate` | Main fraud pipeline |
| GET | `/api/payout/queue` | Officer queue |
| POST | `/api/payout/decision` | Officer decision |
| POST | `/api/query/chat` | Analyst chat |
| POST | `/api/cards/lockdown` | Card lockdown |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + uvicorn |
| Agents | LangChain + Gemini 3-Flash |
| Database | PostgreSQL 16 (asyncpg) |
| Vector DB | ChromaDB |
| ORM | SQLAlchemy 2.0 |
| Frontend | Vue 3 + TypeScript |
