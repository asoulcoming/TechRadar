"""Task scheduler using APScheduler.

Manages periodic tasks:
- Data collection (every 6h)
- Daily report generation (every day at 09:00)
- Breaking hotness detection (every 1h)
- Feishu push (after report generation)
"""

import asyncio
import logging
from datetime import date, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def setup_scheduler(
    supervisor,           # CollectorSupervisor
    hotness_repo,         # HotnessRepository
    report_repo,          # ReportRepository
    feishu_notifier,      # FeishuNotifier
):
    """Register all scheduled tasks.

    Args:
        supervisor: Collector supervisor for data collection
        hotness_repo: Repository for hotness snapshots
        report_repo: Repository for daily reports
        feishu_notifier: Feishu bot for push notifications
    """

    # ── Data Collection (every N hours) ──────────────────────────────
    async def collect_job():
        logger.info("Scheduled collection job started.")
        try:
            results = await supervisor.collect_all_keywords()
            logger.info(f"Scheduled collection complete: {results}")
        except Exception as e:
            logger.error(f"Scheduled collection failed: {e}")

    scheduler.add_job(
        collect_job,
        trigger=IntervalTrigger(hours=settings.COLLECT_INTERVAL_HOURS),
        id="collect_all",
        name="Collect all keywords",
        replace_existing=True,
    )

    # ── Daily Report Generation ─────────────────────────────────────
    async def daily_report_job():
        from notifier.report_generator import generate_daily_report

        logger.info("Generating daily report...")
        try:
            report = await generate_daily_report(hotness_repo, report_repo)
            if report:
                logger.info(f"Daily report generated: {report['title']}")
                # Push to Feishu
                if feishu_notifier.enabled:
                    await feishu_notifier.send_markdown(
                        title=report["title"],
                        content=report["summary"],
                    )
        except Exception as e:
            logger.error(f"Daily report generation failed: {e}")

    # Parse push time from config
    hour, minute = 9, 0
    try:
        parts = settings.DAILY_REPORT_TIME.split(":")
        hour, minute = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        pass

    scheduler.add_job(
        daily_report_job,
        trigger=CronTrigger(hour=hour, minute=minute),
        id="daily_report",
        name="Generate daily report",
        replace_existing=True,
    )

    # ── Breaking Hotness Detection ──────────────────────────────────
    async def breaking_check_job():
        """Check for sudden hotness changes and send alerts."""
        try:
            today = date.today() - timedelta(days=1)
            yesterday = today - timedelta(days=1)

            current = await hotness_repo.get_ranking(today, limit=30)
            prev = await hotness_repo.get_ranking(yesterday, limit=30)

            prev_scores = {t.topic: t.hotness_score for t in prev}
            threshold = settings.BREAKING_THRESHOLD

            for t in current:
                prev_score = prev_scores.get(t.topic, 0)
                if prev_score > 0:
                    change = ((t.hotness_score - prev_score) / prev_score) * 100
                    if abs(change) >= threshold:
                        logger.warning(
                            f"Breaking: {t.topic} on {t.platform} changed {change:+.1f}%"
                        )
                        if feishu_notifier.enabled:
                            await feishu_notifier.send_breaking_alert(
                                topic=t.topic,
                                platform=t.platform,
                                change_percent=change,
                                current_score=t.hotness_score,
                            )
        except Exception as e:
            logger.error(f"Breaking check failed: {e}")

    scheduler.add_job(
        breaking_check_job,
        trigger=IntervalTrigger(hours=1),
        id="breaking_check",
        name="Check for breaking hotness changes",
        replace_existing=True,
    )

    # ── Old Data Cleanup (weekly) ───────────────────────────────────
    async def cleanup_job():
        """Clean up old raw posts (keep hotness snapshots)."""
        logger.info("Running data cleanup...")
        # TODO: Implement cleanup of raw_posts older than retention period
        pass

    scheduler.add_job(
        cleanup_job,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="cleanup",
        name="Weekly data cleanup",
        replace_existing=True,
    )

    logger.info(
        f"Scheduler configured: collection every {settings.COLLECT_INTERVAL_HOURS}h, "
        f"daily report at {settings.DAILY_REPORT_TIME}"
    )
    return scheduler
