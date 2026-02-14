# Nexa - AI-Powered Payments Approval & Fraud Intelligence

Built for the Deriv Hackathon. An intelligent fraud detection system that evaluates every withdrawal through 8 parallel rule indicators, escalating ambiguous cases to LLM-powered investigators for officer review.

## Architecture

```
nexa/
├── fe/          # Nuxt 4 + Tailwind CSS dashboard
└── be/          # FastAPI + LangChain + Gemini backend
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Nuxt 4, TypeScript, Tailwind CSS |
| Backend | FastAPI, LangChain, Gemini |
| Database | PostgreSQL 16 (asyncpg, SQLAlchemy 2.0) |
| Vector DB | ChromaDB |
| Migrations | Alembic |

## Quick Start

### Backend

```bash
cd be
uv sync                          # Install dependencies
docker compose up -d              # Start PostgreSQL + ChromaDB
python -m scripts.seed_data       # Seed test data
uvicorn app.main:app --reload     # Start API server
```

### Frontend

```bash
cd fe
npm install
npm run dev                       # Start dev server
```

## How It Works

1. **Rule Engine (~50ms)** - 8 parallel SQL-based indicators score the withdrawal (0.0-1.0)
2. **Decision Thresholds** - Score < 0.30 auto-approves, >= 0.70 auto-blocks
3. **LLM Investigation (~12s)** - Gray zone (0.30-0.70) escalates to triage router
4. **Investigators** - Financial, Identity, and Cross-Account agents analyze the case
5. **Officer Queue** - Final human decision on escalated cases

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/withdrawals/investigate` | Main fraud pipeline |
| GET | `/api/payout/queue` | Officer review queue |
| POST | `/api/payout/decision` | Officer decision |
| POST | `/api/query/chat` | Analyst chat (natural language) |
| POST | `/api/cards/lockdown` | Fraud ring card lockdown |

## Performance

| Traffic | Latency | LLM Calls |
|---------|---------|-----------|
| Clean (56%) | 0.14s | 0 |
| Suspicious (44%) | 12.1s | 2-3 |
| Blended | ~2.8s | - |
