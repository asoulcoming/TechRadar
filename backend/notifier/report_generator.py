"""Daily tech hotness report generator.

Generates daily Markdown reports summarizing the top tech trends
across all monitored platforms.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from repository.hotness import HotnessRepository
from repository.reports import ReportRepository

logger = logging.getLogger(__name__)


async def generate_daily_report(
    hotness_repo: HotnessRepository,
    report_repo: ReportRepository,
    target_date: date | None = None,
) -> dict | None:
    """Generate a daily tech hotness report.

    Args:
        hotness_repo: Repository for hotness data
        report_repo: Repository for saving reports
        target_date: Date to generate report for (default: yesterday)

    Returns: The generated report dict, or None if already exists.
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    # Check if report already exists
    if await report_repo.exists_for_date(target_date):
        logger.info(f"Report for {target_date} already exists, skipping.")
        return None

    # Aggregate top topics
    top_topics = await hotness_repo.get_top_topics(days=1, limit=10)

    # Get rising topics (compare with previous day)
    prev_date = target_date - timedelta(days=1)
    rising_topics = await _detect_rising_topics(hotness_repo, target_date, prev_date)

    # Get platform highlights
    platform_highlights = await _get_platform_highlights(hotness_repo, target_date)

    # Generate summary (simple template — will use LLM in Phase 2)
    top_names = [t["topic"] for t in top_topics[:5]]
    rising_names = [r["topic"] for r in rising_topics[:3]]

    summary_lines = [
        f"今日概览：{', '.join(top_names[:3])} 等话题热度领先。",
    ]
    if rising_names:
        summary_lines.append(f"{', '.join(rising_names)} 热度快速上升，值得关注。")

    # Build report
    report_title = f"🔥 技术热点日报 | {target_date.isoformat()}"
    report_markdown = _build_report_markdown(
        title=report_title,
        date=target_date,
        top_topics=top_topics,
        rising_topics=rising_topics,
        platform_highlights=platform_highlights,
    )

    # Save to database
    report = await report_repo.save_report({
        "report_date": target_date,
        "title": report_title,
        "summary": report_markdown,
        "top_topics": top_topics,
        "platform_highlights": platform_highlights,
        "rising_topics": rising_topics,
    })

    logger.info(f"Daily report generated: {report_title}")
    return {
        "id": report.id,
        "report_date": target_date.isoformat(),
        "title": report_title,
        "summary": report_markdown,
        "top_topics": top_topics,
        "platform_highlights": platform_highlights,
        "rising_topics": rising_topics,
    }


async def _detect_rising_topics(
    hotness_repo: HotnessRepository,
    current_date: date,
    prev_date: date,
    top_n: int = 5,
) -> list[dict]:
    """Detect topics with the largest hotness increase."""
    current_topics = await hotness_repo.get_ranking(current_date, limit=50)
    prev_topics = await hotness_repo.get_ranking(prev_date, limit=50)

    prev_scores = {t.topic: t.hotness_score for t in prev_topics}
    changes = []

    for t in current_topics:
        prev_score = prev_scores.get(t.topic, 0)
        if prev_score > 0:
            change = ((t.hotness_score - prev_score) / prev_score) * 100
        elif t.hotness_score > 0:
            change = 100.0
        else:
            change = 0.0
        changes.append({
            "topic": t.topic,
            "current_score": t.hotness_score,
            "prev_score": prev_score,
            "change_percent": round(change, 1),
            "platform": t.platform,
        })

    changes.sort(key=lambda x: x["change_percent"], reverse=True)
    return changes[:top_n]


async def _get_platform_highlights(
    hotness_repo: HotnessRepository,
    target_date: date,
) -> list[dict]:
    """Get top topics per platform for highlights section."""
    highlights = []
    for plat in ["bilibili", "xiaohongshu", "zhihu", "github"]:
        topics = await hotness_repo.get_ranking(target_date, plat, limit=3)
        if topics:
            highlights.append({
                "platform": plat,
                "top_topics": [
                    {"topic": t.topic, "score": t.hotness_score}
                    for t in topics
                ],
            })
    return highlights


def _build_report_markdown(
    title: str,
    date: date,
    top_topics: list[dict],
    rising_topics: list[dict],
    platform_highlights: list[dict],
) -> str:
    """Build a Markdown-formatted daily report."""
    lines = [
        f"# {title}",
        "",
        f"> {_generate_overview(top_topics, rising_topics)}",
        "",
        "## 📊 TOP 10 热度主题",
        "",
    ]

    for i, t in enumerate(top_topics[:10], 1):
        emoji = "🔥" if i <= 3 else ("🆕" if t.get("change_percent", 0) > 20 else "")
        lines.append(f"{i}. **{t['topic']}** {emoji} {t['avg_score']}分 — {t['total_posts']}篇相关帖子")

    if rising_topics:
        lines.extend([
            "",
            "## 📈 上升最快",
            "",
        ])
        for r in rising_topics:
            direction = "↑" if r["change_percent"] > 0 else "↓"
            lines.append(f"- **{r['topic']}** {direction}{abs(r['change_percent'])}% — {r['platform']}")

    if platform_highlights:
        lines.extend([
            "",
            "## 🗂 各平台亮点",
            "",
        ])
        plat_names = {"bilibili": "B站", "xiaohongshu": "小红书", "zhihu": "知乎", "github": "GitHub"}
        for h in platform_highlights:
            name = plat_names.get(h["platform"], h["platform"])
            topics_str = ", ".join(
                f"**{t['topic']}**({t['score']}分)" for t in h.get("top_topics", [])
            )
            lines.append(f"- **{name}**: {topics_str}")

    lines.extend([
        "",
        "---",
        f"🤖 由 AI 热点洞察 Agent 自动生成 | {date.isoformat()}",
    ])

    return "\n".join(lines)


def _generate_overview(top_topics: list[dict], rising_topics: list[dict]) -> str:
    """Generate a one-line overview summary."""
    parts = []
    if top_topics:
        names = [t["topic"] for t in top_topics[:3]]
        parts.append(f"{', '.join(names)} 领跑热度榜")
    if rising_topics:
        names = [r["topic"] for r in rising_topics[:2]]
        parts.append(f"{', '.join(names)} 热度上升最快")
    return "；".join(parts) if parts else "技术热点日报"
