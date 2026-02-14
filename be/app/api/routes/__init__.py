"""
API route registration — all routers mounted under /api prefix.

Endpoint Map:
  POST /api/payout/evaluate        — Score a withdrawal request
  GET  /api/payout/queue           — Get review queue for officers
  POST /api/payout/decision        — Officer approves/blocks
  GET  /api/alerts                 — Get fraud alerts
  POST /api/alerts/bulk-action     — Lock accounts, freeze withdrawals
  GET  /api/dashboard/stats        — Dashboard overview numbers
  POST /api/query                  — Natural language fraud search
  GET  /api/health                 — Health check
  GET  /api/transactions           — Paginated withdrawal history
  GET  /api/transactions/export    — Download as CSV
  GET  /api/customers              — List all customers
  GET  /api/customers/{id}/risk-posture             — Current posture
  POST /api/customers/{id}/risk-posture/recompute   — Manual recompute
  GET  /api/customers/{id}/risk-posture/history      — Posture history
  POST /api/prefraud/recompute-all                   — Bulk recompute
  GET  /api/patterns                                 — List patterns
  GET  /api/patterns/{id}                            — Pattern detail
  POST /api/patterns/{id}/activate                   — Activate pattern
  POST /api/patterns/{id}/disable                    — Disable pattern
  POST /api/patterns/detect                          — Manual detection run
  GET  /api/patterns/{id}/graph                      — Pattern graph
  GET  /api/customers/{id}/network                   — Customer network graph
"""
from fastapi import APIRouter

from app.api.routes.fraud import investigate, payout, withdrawal_submit
from app.api.routes.prefraud import prefraud, patterns, background_audits
from app.api.routes.control import alerts, customer_weights
from app.api.routes.analytics import dashboard, query, transactions
from app.api.routes.customer import customers
from app.api.routes.settings import settings
from app.api.routes.system import health

api_router = APIRouter(prefix="/api")

api_router.include_router(payout.router)
api_router.include_router(alerts.router)
api_router.include_router(dashboard.router)
api_router.include_router(query.router)
api_router.include_router(health.router)
api_router.include_router(transactions.router)
api_router.include_router(withdrawal_submit.router)
api_router.include_router(investigate.router)
api_router.include_router(customers.router)
api_router.include_router(customer_weights.router)
api_router.include_router(settings.router)
api_router.include_router(background_audits.router)
api_router.include_router(prefraud.customer_posture_router)
api_router.include_router(prefraud.prefraud_router)
api_router.include_router(patterns.pattern_router)
api_router.include_router(patterns.customer_network_router)
