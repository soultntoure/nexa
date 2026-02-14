"""Background audit facade — orchestrates the full pipeline."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from langchain_core.tools import BaseTool
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agentic_system.agents.background_audit_agent import BackgroundAuditAgent
from app.agentic_system.agents.weight_drift_agent import WeightDriftAgent
from app.agentic_system.tools.kmeans_tool import KMeansClusterTool
from app.agentic_system.tools.web_search_tool import create_web_search_tool
from app.config import get_settings
from app.core.background_audit.dataset_prep import (
    compute_run_fingerprint,
    compute_window,
    generate_run_id,
    validate_window,
)
from app.data.db.models.audit_run import AuditRun
from app.data.db.repositories.audit_config_repository import AuditConfigRepository
from app.data.db.repositories.audit_run_repository import AuditRunRepository
from app.services.background_audit.components.candidate_report import generate_candidates
from app.services.background_audit.components.weight_drift_analysis import run_weight_drift_analysis
from app.services.background_audit.components.embed_cluster import embed_and_cluster
from app.services.background_audit.components.extract import extract_cohort
from app.services.background_audit.progress import SSEEvent, build_event
from app.services.background_audit.queries import BackgroundAuditQueries

logger = logging.getLogger(__name__)


class BackgroundAuditFacade(BackgroundAuditQueries):
    """Single entry point for background audit operations."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        super().__init__(session_factory)
        self._running_task: asyncio.Task[None] | None = None
        self._progress_queues: dict[str, asyncio.Queue[SSEEvent | None]] = {}

    def attach_progress(self, run_id: str) -> asyncio.Queue[SSEEvent | None]:
        """Create and return a queue for SSE progress events."""
        queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()
        self._progress_queues[run_id] = queue
        return queue

    def detach_progress(self, run_id: str) -> None:
        """Remove a progress queue for the given run."""
        self._progress_queues.pop(run_id, None)

    async def _emit(self, run_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Push an SSE event to the run's queue if attached."""
        queue = self._progress_queues.get(run_id)
        if not queue:
            return
        evt = build_event(event_type, **data)
        await queue.put(evt)

    async def _load_run_config(self, settings: Any) -> dict[str, Any]:
        """Load active DB config merged with env defaults."""
        async with self._sf() as session:
            repo = AuditConfigRepository(session)
            db_cfg = await repo.get_active()
        if db_cfg:
            return {
                "lookback_days": db_cfg.lookback_days,
                "max_candidates": db_cfg.max_candidates,
                "output_dir": db_cfg.output_dir,
                "min_events": db_cfg.min_events,
                "min_accounts": db_cfg.min_accounts,
                "min_confidence": db_cfg.min_confidence,
                "cluster_min_size": settings.BACKGROUND_AUDIT_CLUSTER_MIN_SIZE,
                "cluster_min_samples": settings.BACKGROUND_AUDIT_CLUSTER_MIN_SAMPLES,
                "cluster_merge_similarity": settings.BACKGROUND_AUDIT_CLUSTER_MERGE_SIMILARITY,
                "cluster_normalize_embeddings": settings.BACKGROUND_AUDIT_CLUSTER_NORMALIZE_EMBEDDINGS,
            }
        return {
            "lookback_days": settings.BACKGROUND_AUDIT_LOOKBACK_DAYS,
            "max_candidates": settings.BACKGROUND_AUDIT_MAX_CANDIDATES,
            "output_dir": settings.BACKGROUND_AUDIT_OUTPUT_DIR,
            "min_events": 5,
            "min_accounts": 2,
            "min_confidence": 0.50,
            "cluster_min_size": settings.BACKGROUND_AUDIT_CLUSTER_MIN_SIZE,
            "cluster_min_samples": settings.BACKGROUND_AUDIT_CLUSTER_MIN_SAMPLES,
            "cluster_merge_similarity": settings.BACKGROUND_AUDIT_CLUSTER_MERGE_SIMILARITY,
            "cluster_normalize_embeddings": settings.BACKGROUND_AUDIT_CLUSTER_NORMALIZE_EMBEDDINGS,
        }

    async def trigger_run(
        self, lookback_days: int | None = None, run_mode: str = "full",
    ) -> str:
        """Start a background audit run. Returns run_id."""
        settings = get_settings()
        cfg = await self._load_run_config(settings)
        days = lookback_days or cfg["lookback_days"]
        window = compute_window(days)

        if not validate_window(window):
            raise ValueError("Invalid run window")

        run_id = generate_run_id()
        idempotency_key = compute_run_fingerprint(window, run_mode)

        cfg["lookback_days"] = days  # override with explicit param

        async with self._sf() as session:
            repo = AuditRunRepository(session)
            existing = await repo.get_by_idempotency_key(idempotency_key)
            if existing and existing.status in ("running", "completed"):
                return existing.run_id

            run = AuditRun(
                run_id=run_id,
                status="pending",
                run_mode=run_mode,
                config_snapshot=cfg,
                idempotency_key=idempotency_key,
            )
            await repo.create(run)

        self._running_task = asyncio.create_task(
            self._run_pipeline(run_id, window, run_mode, cfg),
        )
        return run_id

    async def _run_pipeline(
        self, run_id: str, window: Any, run_mode: str,
        cfg: dict[str, Any] | None = None,
    ) -> None:
        """Execute extract -> embed -> cluster -> investigate pipeline."""
        settings = get_settings()
        timings: dict[str, float] = {}

        async with self._sf() as session:
            repo = AuditRunRepository(session)
            await repo.update_status(run_id, "running")

        async def emit(event_type: str, data: dict[str, Any]) -> None:
            await self._emit(run_id, event_type, data)

        try:
            units, clusters, candidates = await self._execute_phases(
                run_id, window, settings, timings, emit, cfg=cfg,
            )
            drift_count = sum(1 for c in candidates if (c.pattern_card or {}).get("drift_data"))
            counters = {
                "units_extracted": len(units),
                "clusters_found": len(clusters),
                "candidates_generated": len(candidates),
                "drift_candidates_generated": drift_count,
            }
            async with self._sf() as session:
                repo = AuditRunRepository(session)
                await repo.update_status(run_id, "completed", counters=counters, timings=timings)

            pattern_count = len(candidates) - drift_count
            await emit("complete", {
                "title": "Audit complete",
                "detail": f"{pattern_count} patterns found across {len(clusters)} groups",
                "narration": f"Investigation finished. Identified {pattern_count} fraud patterns that need attention.",
            })
            logger.info("Audit run %s completed: %s", run_id, counters)

        except Exception as exc:
            logger.error("Audit run %s failed: %s", run_id, exc, exc_info=True)
            await emit("error", {"title": "Pipeline failed", "detail": str(exc)})
            async with self._sf() as session:
                repo = AuditRunRepository(session)
                await repo.update_status(run_id, "failed", error_message=str(exc), timings=timings)
        finally:
            queue = self._progress_queues.get(run_id)
            if queue:
                await queue.put(None)

    async def _execute_phases(
        self, run_id: str, window: Any, settings: Any,
        timings: dict[str, float], emit: Any,
        cfg: dict[str, Any] | None = None,
    ) -> tuple[list, list, list]:
        """Run extract -> embed/cluster -> investigate."""
        max_candidates = (cfg or {}).get("max_candidates", settings.BACKGROUND_AUDIT_MAX_CANDIDATES)
        quality_gate = {
            "min_events": (cfg or {}).get("min_events", 5),
            "min_accounts": (cfg or {}).get("min_accounts", 2),
            "min_confidence": (cfg or {}).get("min_confidence", 0.50),
        }
        cluster_min_samples = (cfg or {}).get(
            "cluster_min_samples",
            settings.BACKGROUND_AUDIT_CLUSTER_MIN_SAMPLES,
        )
        if isinstance(cluster_min_samples, int) and cluster_min_samples <= 0:
            cluster_min_samples = None
        cluster_config = {
            "min_cluster_size": (cfg or {}).get(
                "cluster_min_size",
                settings.BACKGROUND_AUDIT_CLUSTER_MIN_SIZE,
            ),
            "min_samples": cluster_min_samples,
            "merge_similarity": (cfg or {}).get(
                "cluster_merge_similarity",
                settings.BACKGROUND_AUDIT_CLUSTER_MERGE_SIMILARITY,
            ),
            "normalize_embeddings": (cfg or {}).get(
                "cluster_normalize_embeddings",
                settings.BACKGROUND_AUDIT_CLUSTER_NORMALIZE_EMBEDDINGS,
            ),
        }

        t0 = time.monotonic()
        await emit("phase_start", {
            "title": "Scanning recent transactions...",
            "phase": "extract",
            "narration": "Reviewing recent fraud evaluations to find suspicious activity worth investigating.",
        })
        units = await extract_cohort(window, self._sf)
        timings["extract_s"] = round(time.monotonic() - t0, 2)
        await emit("progress", {
            "title": "Scan complete",
            "phase": "extract",
            "detail": f"Found {len(units)} pieces of evidence to analyze",
            "narration": f"Collected {len(units)} fraud signals from recent evaluations.",
            "progress": 1.0,
        })

        t1 = time.monotonic()
        await emit("phase_start", {
            "title": "Grouping suspicious patterns...",
            "phase": "embed_cluster",
            "narration": "Comparing evidence to find which cases share similar fraud characteristics.",
        })
        clusters = await embed_and_cluster(units, self._sf, **cluster_config)
        timings["embed_cluster_s"] = round(time.monotonic() - t1, 2)
        await emit("progress", {
            "title": "Grouping complete",
            "phase": "embed_cluster",
            "detail": f"Discovered {len(clusters)} distinct patterns",
            "narration": f"Found {len(clusters)} groups of related suspicious activity to investigate.",
            "progress": 1.0,
        })

        t2 = time.monotonic()
        await emit("phase_start", {
            "title": "Analyzing each pattern...",
            "phase": "investigate",
            "narration": "An AI agent will now deep-dive into each suspicious group to determine what happened.",
        })
        tools, schema_docs = _build_agent_tools(settings)
        agent = BackgroundAuditAgent(tools=tuple(tools), schema_docs=schema_docs)
        drift_agent = WeightDriftAgent(tools=tuple(tools), schema_docs=schema_docs)

        candidates_list, drift_candidates = await asyncio.gather(
            generate_candidates(
                clusters, run_id, self._sf, agent=agent,
                max_candidates=max_candidates, emit=emit,
                quality_gate_config=quality_gate,
            ),
            run_weight_drift_analysis(
                run_id, window, self._sf, agent=drift_agent, emit=emit,
            ),
        )
        all_candidates = list(candidates_list) + list(drift_candidates)
        timings["candidate_report_s"] = round(time.monotonic() - t2, 2)
        return units, clusters, all_candidates


def _build_sync_uri(async_url: str) -> str:
    """Convert asyncpg URL to psycopg2 URL, stripping unsupported params."""
    uri = async_url.replace("+asyncpg", "")
    if "?" in uri:
        base, qs = uri.split("?", 1)
        params = [p for p in qs.split("&") if not p.startswith("ssl=")]
        uri = f"{base}?{'&'.join(params)}" if params else base
    return uri


def _build_agent_tools(settings: Any) -> tuple[list[BaseTool], str]:
    """Build tools and live schema docs for the autonomous audit agent."""
    tools: list[BaseTool] = []
    schema_docs = ""

    web_tool = create_web_search_tool(settings.TAVILY_API_KEY)
    if web_tool:
        tools.append(web_tool)

    tools.append(KMeansClusterTool())

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        from app.agentic_system.tools.sql.schema_builder import (
            build_critical_notes,
            build_pg_cheat_sheet,
            build_schema_description,
        )
        from app.agentic_system.tools.sql.toolkit import FRAUD_DB_TABLES, create_sql_toolkit, get_query_tools
        sync_uri = _build_sync_uri(settings.POSTGRES_URL)
        sync_engine = create_engine(sync_uri)
        schema_docs = build_schema_description(sync_engine, FRAUD_DB_TABLES) + build_critical_notes() + build_pg_cheat_sheet()
        llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0.0)
        toolkit = create_sql_toolkit(sync_uri, llm)
        tools.extend(get_query_tools(toolkit))
    except Exception:
        logger.warning("SQL tools unavailable for audit agent", exc_info=True)

    return tools, schema_docs
