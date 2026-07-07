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
    """Manually trigger daily report generation for a specific date."""
    hotness_repo = HotnessRepository(db)
    report_repo = ReportRepository(db)

    dt = date.fromisoformat(target_date) if target_date else date.today() - timedelta(days=1)

    report = await generate_daily_report(hotness_repo, report_repo, dt)
    if report is None:
        return {"status": "skipped", "message": f"Report for {dt} already exists"}

    # Push to Feishu if configured
    if settings.FEISHU_WEBHOOK_URL:
        feishu = FeishuNotifier(settings.FEISHU_WEBHOOK_URL, settings.FEISHU_SECRET)
        await feishu.send_markdown(title=report["title"], content=report["summary"])
        await feishu.close()

    return {"status": "ok", "report": report}
