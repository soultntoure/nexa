"""
Pydantic Settings — env-based configuration.

Contains:
- Settings class using pydantic-settings BaseSettings
- DB connection string (POSTGRES_URL)
- ChromaDB path/config
- Google AI API key for LangChain agents
- App-level settings: debug, log_level, cors origins
- Threshold defaults (approve/escalate/block boundaries)

Usage: `settings = get_settings()` via DI in deps.py
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──
    POSTGRES_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/deriv_fraud_detection"
    )

    # ── ChromaDB ──
    CHROMADB_HOST: str = "localhost"
    CHROMADB_PORT: int = 8000

    # ── Google AI ──
    GOOGLE_API_KEY: str = ""

    # ── Tavily (web search) ──
    TAVILY_API_KEY: str = ""

    # ── App ──
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = ["*"]

    # ── Threshold defaults ──
    DEFAULT_BLOCK_THRESHOLD: float = 0.80
    DEFAULT_ESCALATE_THRESHOLD: float = 0.45

    # ── Feature flags ──
    BACKGROUND_AUDIT_ENABLED: bool = False

    # ── Background Audit ──
    BACKGROUND_AUDIT_OUTPUT_DIR: str = "outputs/background_audits/stage_1"
    BACKGROUND_AUDIT_MAX_CANDIDATES: int = 50
    BACKGROUND_AUDIT_LOOKBACK_DAYS: int = 7
    BACKGROUND_AUDIT_CLUSTER_MIN_SIZE: int = 8
    BACKGROUND_AUDIT_CLUSTER_MIN_SAMPLES: int = 4
    BACKGROUND_AUDIT_CLUSTER_MERGE_SIMILARITY: float = 0.90
    BACKGROUND_AUDIT_CLUSTER_NORMALIZE_EMBEDDINGS: bool = True

    # ── Pre-Fraud Posture ──
    POSTURE_INFLUENCE_ENABLED: bool = False  # Shadow mode by default
    POSTURE_RECOMPUTE_INTERVAL_S: int = 3600  # Scheduled loop interval
    POSTURE_DEBOUNCE_S: int = 5  # Min seconds between event-driven recomputes

    # ── Pattern Detection (Phase 2) ──
    PATTERN_DETECTION_ENABLED: bool = True
    PATTERN_SCORING_ENABLED: bool = False  # Shadow mode by default
    PATTERN_DETECTION_INTERVAL_S: int = 43200  # 12 hours


@lru_cache
def get_settings() -> Settings:
    return Settings()
