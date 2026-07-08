"""Application configuration management."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent

# Load .env before reading settings
load_dotenv(PROJECT_ROOT / "backend" / ".env")


class Settings:
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{PROJECT_ROOT}/data/agent.db",
    )

    # Collector
    COLLECT_INTERVAL_HOURS: int = int(os.getenv("COLLECT_INTERVAL_HOURS", "6"))
    COLLECT_REQUEST_DELAY_SECONDS: int = int(os.getenv("COLLECT_REQUEST_DELAY_SECONDS", "5"))
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    MEDIACRAWLER_PATH: str = os.getenv(
        "MEDIACRAWLER_PATH",
        str(PROJECT_ROOT.parent / "MediaCrawler"),
    )

    # Agent
    AGENT_MODEL: str = os.getenv("AGENT_MODEL", "claude-sonnet-5")
    AGENT_MAX_ITERATIONS: int = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))

    # Report
    DAILY_REPORT_TIME: str = os.getenv("DAILY_REPORT_TIME", "09:00")
    REPORT_RETENTION_DAYS: int = int(os.getenv("REPORT_RETENTION_DAYS", "90"))

    # Feishu
    FEISHU_WEBHOOK_URL: str = os.getenv("FEISHU_WEBHOOK_URL", "")
    FEISHU_SECRET: str = os.getenv("FEISHU_SECRET", "")
    BREAKING_THRESHOLD: float = float(os.getenv("BREAKING_THRESHOLD", "30.0"))

    # App
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
