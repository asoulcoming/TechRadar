"""Report endpoints."""

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.report import DailyReportOut, ReportListResponse, FeishuConfigRequest
from repository.reports import ReportRepository
from repository.hotness import HotnessRepository
from repository.posts import PostRepository
from notifier.report_generator import generate_daily_report
from notifier.feishu import FeishuNotifier
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports/latest", response_model=DailyReportOut)
async def get_latest_report(db: AsyncSession = Depends(get_db)):
    """Get the latest daily report."""
    repo = ReportRepository(db)
    report = await repo.get_latest()
    if report is None:
        raise HTTPException(status_code=404, detail="No reports generated yet")
    return report


@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    """List daily reports in a date range."""
    start = date.fromisoformat(from_date) if from_date else date.today() - timedelta(days=30)
    end = date.fromisoformat(to_date) if to_date else date.today()

    repo = ReportRepository(db)
    reports = await repo.get_by_date_range(start, end)
    return ReportListResponse(
        reports=[DailyReportOut.model_validate(r) for r in reports],
        total=len(reports),
    )


@router.post("/reports/generate")
async def trigger_report_generation(
    target_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger the full pipeline: import → hotness → report."""
    from analyzer.pipeline import run_data_pipeline

    post_repo = PostRepository(db)
    hotness_repo = HotnessRepository(db)
    report_repo = ReportRepository(db)

    dt = date.fromisoformat(target_date) if target_date else date.today() - timedelta(days=1)

    # Step 1: Run data pipeline (import MediaCrawler data + compute hotness)
    pipeline_result = await run_data_pipeline(
        post_repo=post_repo,
        hotness_repo=hotness_repo,
        target_date=dt,
    )

    # Step 2: Generate report from hotness data
    report = await generate_daily_report(hotness_repo, report_repo, dt)
    if report is None:
        return {
            "status": "skipped",
            "message": f"Report for {dt} already exists",
            "pipeline": pipeline_result,
        }

    # Push to Feishu if configured
    if settings.FEISHU_WEBHOOK_URL:
        feishu = FeishuNotifier(settings.FEISHU_WEBHOOK_URL, settings.FEISHU_SECRET)
        await feishu.send_markdown(title=report["title"], content=report["summary"])
        await feishu.close()

    return {
        "status": "ok",
        "report": report,
        "pipeline": pipeline_result,
    }


# ── Feishu Config endpoints ──────────────────────────────────────────


@router.get("/config/feishu")
async def get_feishu_config(db: AsyncSession = Depends(get_db)):
    """Get current Feishu bot configuration from database."""
    from repository.models import FeishuConfig
    from sqlalchemy import select as sa_select
    result = await db.execute(sa_select(FeishuConfig).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        return {
            "webhook_url": settings.FEISHU_WEBHOOK_URL,
            "secret": "",
            "push_daily_report": True,
            "push_breaking": True,
            "breaking_threshold": settings.BREAKING_THRESHOLD,
            "push_time": settings.DAILY_REPORT_TIME,
            "source": "env",
        }
    return {
        "webhook_url": config.webhook_url,
        "secret": config.secret,
        "push_daily_report": config.push_daily_report,
        "push_breaking": config.push_breaking,
        "breaking_threshold": config.breaking_threshold,
        "push_time": config.push_time,
        "source": "db",
    }


@router.put("/config/feishu")
async def update_feishu_config(
    body: FeishuConfigRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update Feishu bot configuration."""
    from repository.models import FeishuConfig
    from sqlalchemy import select as sa_select
    result = await db.execute(sa_select(FeishuConfig).limit(1))
    config = result.scalar_one_or_none()

    if config:
        for key, val in body.model_dump().items():
            setattr(config, key, val)
    else:
        config = FeishuConfig(**body.model_dump())
        db.add(config)

    await db.commit()
    logger.info("Feishu config updated")
    return {"status": "ok", "message": "Feishu configuration updated"}


@router.post("/config/feishu/test")
async def test_feishu_push():
    """Send a test message to Feishu to verify webhook configuration."""
    if not settings.FEISHU_WEBHOOK_URL:
        raise HTTPException(
            status_code=400,
            detail="Feishu webhook URL not configured. Set FEISHU_WEBHOOK_URL in .env or update via PUT /api/config/feishu",
        )

    feishu = FeishuNotifier(settings.FEISHU_WEBHOOK_URL, settings.FEISHU_SECRET)
    success = await feishu.send_text(
        "✅ AI 热点洞察 Agent 飞书推送测试成功！\n\n如果您看到这条消息，说明 Webhook 配置正确。",
        at_all=False,
    )
    await feishu.close()

    if success:
        return {"status": "ok", "message": "Test message sent to Feishu"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test message")
