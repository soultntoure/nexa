# Card Lockdown Feature

**Status**: Implemented (Feb 2026)

When a compliance officer reviews an alert for a blocked withdrawal where the customer's card is shared with other accounts, they can execute a "Card Lockdown" to flag all linked accounts, blacklist the shared cards, and auto-generate alerts.

## Documentation

| File | What it covers |
|------|---------------|
| `01_workflow.md` | End-to-end workflow diagrams (officer perspective) |
| `02_backend_architecture.md` | Service, repository, route — sequence diagrams + data flow |
| `03_data_model.md` | Database tables, match criteria, seed data |
| `04_api_contract.md` | Endpoint specs, request/response schemas |

## Key Files

| Layer | File |
|-------|------|
| Route | `app/api/routes/alerts.py` |
| Service | `app/services/control/card_lockdown_service.py` |
| Repository | `app/data/db/repositories/payment_method_repository.py` |
| Frontend | `nexa-fe/pages/alerts.vue` |
| Notifications | `nexa-fe/components/common/NotificationDropdown.vue` |
| Proxy (check) | `nexa-fe/server/api/alerts/card-check/[externalId].get.ts` |
| Proxy (lockdown) | `nexa-fe/server/api/alerts/card-lockdown.post.ts` |

## Performance

| Operation | Latency |
|-----------|---------|
| GET /card-check | ~50ms |
| POST /card-lockdown | ~200-500ms |
| Alert poll (30s interval) | ~100ms |
