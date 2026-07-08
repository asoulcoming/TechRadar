"""FastAPI application entry point.

Start with: uvicorn main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import init_db
from api.chat import router as chat_router
from api.trends import router as trends_router
from api.topics import router as topics_router
from api.dashboard import router as dashboard_router
from api.reports import router as reports_router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Scheduler will be started after DB init ────────────────────────
_scheduler_started = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    global _scheduler_started

    # Startup
    logger.info("Starting AI Hotspot Agent Platform...")
    await init_db()
    logger.info("Database tables initialized.")

    # Start scheduler (imported here to avoid circular imports)
    try:
        from notifier.scheduler import setup_scheduler, scheduler
        from collector.supervisor import CollectorSupervisor
        from repository.posts import PostRepository
        from repository.hotness import HotnessRepository
        from repository.reports import ReportRepository
        from notifier.feishu import FeishuNotifier
        from db import async_session

        # Create dependencies for scheduler
        async with async_session() as db:
            post_repo = PostRepository(db)
            hotness_repo = HotnessRepository(db)
            report_repo = ReportRepository(db)
            supervisor = CollectorSupervisor(post_repo=post_repo)
            feishu = FeishuNotifier(
                webhook_url=settings.FEISHU_WEBHOOK_URL,
                secret=settings.FEISHU_SECRET,
            )

            setup_scheduler(
                supervisor, hotness_repo, report_repo, feishu,
                post_repo=post_repo,
            )
            scheduler.start()

        _scheduler_started = True
        logger.info("Task scheduler started.")
    except Exception as e:
        logger.warning(f"Scheduler not started (this is OK for MVP): {e}")

    yield

    # Shutdown
    if _scheduler_started:
        try:
            from notifier.scheduler import scheduler
            scheduler.shutdown(wait=False)
            logger.info("Task scheduler stopped.")
        except Exception:
            pass

    logger.info("Shutting down.")


app = FastAPI(
    title="AI 热点洞察 Agent 平台",
    description="计算机技术领域热点追踪与趋势分析 Agent",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(chat_router)
app.include_router(trends_router)
app.include_router(topics_router)
app.include_router(dashboard_router)
app.include_router(reports_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "0.1.0",
        "scheduler": _scheduler_started,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.DEBUG)
