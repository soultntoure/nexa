# Investigator Service Persistence View

This view explains where persistence happens for `app/services/fraud/investigator_service.py` and how rule-based and LLM-based outputs are stored.

## 1) Persistence sequence

```mermaid
sequenceDiagram
    participant API as investigate route
    participant WS as withdrawal_service
    participant IS as InvestigatorService
    participant RE as Rule Engine
    participant LLM as Triage + Investigators
    participant WR as WithdrawalRepository
    participant DB as PostgreSQL

    API->>WS: ensure_withdrawal_exists(...)
    WS->>DB: INSERT withdrawals (if missing)

    API->>IS: investigate(request)
    IS->>RE: run_all_indicators(...)
    RE-->>IS: rule IndicatorResult[]

    alt Rule decision is escalated
        IS->>LLM: _run_triage(context)
        LLM-->>IS: assignments
        IS->>LLM: _run_investigators(assignments)
        LLM-->>IS: investigator findings
    else Rule decision approved/blocked
        IS-->>IS: skip triage and investigators
    end

    IS->>IS: _build_investigation_data(...)
    IS->>WR: save_evaluation(Evaluation)
    WR->>DB: INSERT evaluations + COMMIT

    IS->>WR: save_indicator_results(db_indicators)
    WR->>DB: INSERT indicator_results + COMMIT

    IS-->>API: evaluation_id + decision + score
    API->>WS: update_withdrawal_status(...)
    WS->>DB: UPDATE withdrawals.status + COMMIT
```

## 2) Rule-based vs LLM-based storage

```mermaid
flowchart TD
    A[run_all_indicators] --> B[Rule scoring]
    B --> C{Rule decision}
    C -->|approved or blocked| D[LLM skipped]
    C -->|escalated| E[Triage LLM]
    E --> F[0 to 3 investigator LLM calls]
    D --> G[_persist]
    F --> G[_persist]

    G --> H[evaluations row]
    G --> I[indicator_results rows]

    H --> H1[decision + composite_score + summary]
    H --> H2[investigation_data JSONB]
    H2 --> H3[rule_engine snapshot]
    H2 --> H4[triage assignments]
    H2 --> H5[investigator findings]

    I --> I1[only rule indicator outputs]
```

## Exactly where writes happen

- `InvestigatorService._persist(...)` is the main persistence method.
- `WithdrawalRepository.save_evaluation(...)` commits the `evaluations` row.
- `WithdrawalRepository.save_indicator_results(...)` commits `indicator_results` rows.
- Route-level `update_withdrawal_status(...)` commits `withdrawals.status`.
- `withdrawal_decisions` is not written by `InvestigatorService`; officer decisions are written in `app/services/control/decision_service.py` via `submit_decision(...)`.

## Important persistence nuance

- `_persist(...)` uses two separate commits: first `evaluations`, then `indicator_results`.
- If the second commit fails, the evaluation row can still exist while indicator rows are missing for that run.
