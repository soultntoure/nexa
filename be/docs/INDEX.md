# Documentation Index

**Last Updated**: Feb 12, 2026

## Directory Structure

```
docs/
├── INDEX.md                                    <- You are here
├── README.md                                   <- Project overview + system diagram + all endpoints
│
├── architecture/                               <- System design & diagrams
│   ├── component_diagram.md                    <- Full system component diagram (Mermaid)
│   ├── problem_statement.md                    <- Challenge, solution, stack, constraints
│   ├── payout_state_machine.md                 <- Withdrawal lifecycle state machine
│   ├── vpn_detection.md                        <- Why VPN is mocked, production path
│   └── seeding_scenarios.md                    <- 16 test customer profiles
│
├── features/                                   <- IMPLEMENTED features (code exists)
│   ├── fraud_detection/                        <- Fraud Detection Pipelines
│   │   ├── README.md                           <- Feature overview + performance
│   │   ├── investigator_pipeline.md            <- End-to-end pipeline flow with diagrams
│   │   └── agentic_system.md                   <- Triage router + 3 investigators
│   │
│   ├── chat/                                   <- Analyst Chat + Chart Visualization
│   │   ├── README.md                           <- Feature overview + performance
│   │   ├── streaming_flow.md                   <- Workflow + sequence diagrams
│   │   └── sse_event_contract.md               <- SSE event lifecycle + payload schemas
│   │
│   ├── card_lockdown/                          <- Card Lockdown (shared card detection)
│   │   ├── README.md                           <- Feature overview + key files
│   │   ├── workflow.md                         <- Officer walkthrough + diagrams
│   │   ├── backend_architecture.md             <- Service/repo layer + sequence diagrams
│   │   ├── data_model.md                       <- DB tables, match criteria, seed data
│   │   └── api_contract.md                     <- Endpoint specs + request/response
│   │
│   ├── weights_config/                         <- Adaptive Customer Weights
│   │   ├── overview.md                         <- High-level loop + workflow diagrams
│   │   ├── design_module.md                    <- Full calibration cycle + all diagrams
│   │   └── implementation_guide.md             <- Status, files built, seeded profiles
│   │
│   └── background_audits/                      <- Background Audit Pipeline
│       ├── README.md                           <- Feature overview + reading order
│       ├── trigger_and_facade.md               <- API trigger, facade, run lifecycle
│       ├── extract_phase.md                    <- Cohort query, PII masking, dedup
│       ├── embed_and_cluster.md                <- Gemini embeddings, HDBSCAN, novelty
│       ├── candidates_and_artifacts.md         <- Quality gates, agent synthesis, artifacts
│       ├── scoring_and_clustering.md           <- All formulas + text processing
│       ├── api_and_data.md                     <- Endpoints, DB models, JSONB schemas
│       └── next_up.md                          <- Stage 2: autonomous agent roadmap
│
├── planning/                                   <- PLANNED features (no code yet)
│   ├── README.md                               <- Planning overview
│   ├── background_audits/                      <- Background audit Stage 2 design
│   │   ├── README.md
│   │   ├── stage_1/                            <- Scope, jobs, pipeline, output contract
│   │   ├── stage_2/                            <- Reintegration, observability
│   │   └── agentic_cycle/                      <- LangGraph state, tools, nodes
│   │
│   └── predictive_fraud/                       <- ML-based predictive fraud
│       ├── README.md
│       ├── 01-05 strategy docs
│       ├── predictive_blocking/
│       └── tech_impl/                          <- 7 technical implementation specs
│
└── database/                                   <- Database schema documentation
    ├── README.md                               <- Schema overview + reading order
    ├── customer_and_activity.md                <- Customers, sessions, devices
    ├── withdrawal_risk_pipeline.md             <- Evaluations, indicator results
    ├── review_feedback_alerts.md               <- Officer decisions, alerts
    ├── config_and_learning.md                  <- Weights, thresholds, learning
    └── investigator_service_persistence.md     <- Investigation JSONB data
```

---

## Quick Navigation

### Implemented Features

| Feature | Docs | Code |
|---------|------|------|
| Fraud Detection (New Pipeline) | [features/fraud_detection/](features/fraud_detection/) | `app/services/fraud/investigator_service.py` |
| Fraud Detection (Old Pipeline) | [features/fraud_detection/](features/fraud_detection/) | `app/services/fraud/check_service.py` |
| Analyst Chat + Charts | [features/chat/](features/chat/) | `app/services/chat/streaming_service.py` |
| Card Lockdown | [features/card_lockdown/](features/card_lockdown/) | `app/services/control/card_lockdown_service.py` |
| Customer Weights | [features/weights_config/](features/weights_config/) | `app/services/control/customer_weight_explain_service.py` |
| Background Audits | [features/background_audits/](features/background_audits/) | `app/services/audit/` |
| Officer Queue | [README.md](README.md) | `app/services/dashboard/queue_mapper.py` |
| Threshold Config | [features/weights_config/](features/weights_config/) | `app/services/control/threshold_service.py` |
| Feedback Loop | [features/weights_config/overview.md](features/weights_config/overview.md) | `app/services/control/feedback_loop_service.py` |
| 8 Rule Indicators | [architecture/problem_statement.md](architecture/problem_statement.md) | `app/core/indicators/` |

### Planned Features (No Code)

| Feature | Docs | Status |
|---------|------|--------|
| Background Audit Stage 2 | [planning/background_audits/](planning/background_audits/) | Design phase |
| Predictive Fraud / ML Blocking | [planning/predictive_fraud/](planning/predictive_fraud/) | Design phase |

### Architecture & Reference

| Topic | Location |
|-------|----------|
| System component diagram | [architecture/component_diagram.md](architecture/component_diagram.md) |
| Problem statement + stack | [architecture/problem_statement.md](architecture/problem_statement.md) |
| Withdrawal state machine | [architecture/payout_state_machine.md](architecture/payout_state_machine.md) |
| VPN detection approach | [architecture/vpn_detection.md](architecture/vpn_detection.md) |
| Test customer scenarios | [architecture/seeding_scenarios.md](architecture/seeding_scenarios.md) |

### Database

| Topic | Location |
|-------|----------|
| Schema overview | [database/README.md](database/README.md) |
| Customer + activity tables | [database/customer_and_activity.md](database/customer_and_activity.md) |
| Withdrawal risk pipeline | [database/withdrawal_risk_pipeline.md](database/withdrawal_risk_pipeline.md) |
| Review + feedback + alerts | [database/review_feedback_alerts.md](database/review_feedback_alerts.md) |
| Config + learning tables | [database/config_and_learning.md](database/config_and_learning.md) |
| Investigation data (JSONB) | [database/investigator_service_persistence.md](database/investigator_service_persistence.md) |

---

## Code Quick Reference

| Feature | Code Location |
|---------|---------------|
| New fraud pipeline | `app/services/fraud/investigator_service.py` |
| Old fraud pipeline | `app/services/fraud/check_service.py` |
| 8 rule indicators | `app/core/indicators/` |
| Scoring + thresholds | `app/core/scoring.py` |
| Triage + investigators | `app/agentic_system/prompts/` |
| Analyst chat SSE | `app/services/chat/streaming_service.py` |
| Chart generation | `app/services/chat/charting/` |
| Card lockdown | `app/services/control/card_lockdown_service.py` |
| Customer weights | `app/services/control/customer_weight_explain_service.py` |
| Feedback loop | `app/services/control/feedback_loop_service.py` |
| Officer queue | `app/services/dashboard/queue_mapper.py` |
| Background audits | `app/services/audit/` |
