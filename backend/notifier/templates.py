"""Message templates for Feishu notifications."""

from datetime import date
from typing import Optional


def daily_report_template(
    report_date: date,
    top_topics: list[dict],
    rising_topics: list[dict],
    platform_highlights: list[dict],
) -> str:
    """Build a Markdown daily report for Feishu push.

    Feishu supports a subset of Markdown — keep it simple.
    """
    lines = [
        f"🔥 技术热点日报 | {report_date.isoformat()}",
        "",
    ]

    if top_topics:
        lines.append("📊 **今日 TOP 5**")
        for i, t in enumerate(top_topics[:5], 1):
            emoji = "🆕" if t.get("change_percent", 0) > 20 else ""
            lines.append(f"{i}. **{t['topic']}** {emoji} {t['avg_score']}分")
        lines.append("")

    if rising_topics:
        lines.append("📈 **上升最快**")
        for r in rising_topics[:3]:
            direction = "↑" if r["change_percent"] > 0 else "↓"
            lines.append(f"- **{r['topic']}** {direction}{abs(r['change_percent'])}%")
        lines.append("")

    if platform_highlights:
        plat_names = {
            "bilibili": "B站", "xiaohongshu": "小红书",
            "zhihu": "知乎", "github": "GitHub",
        }
        lines.append("🗂 **各平台亮点**")
        for h in platform_highlights:
            name = plat_names.get(h["platform"], h["platform"])
            topics_str = ", ".join(
                f"**{t['topic']}**" for t in h.get("top_topics", [])[:2]
            )
            lines.append(f"- {name}: {topics_str}")
        lines.append("")

    lines.append(f"🤖 由 AI 热点洞察 Agent 自动生成")

    return "\n".join(lines)


def breaking_alert_template(
    topic: str,
    platform: str,
    change_percent: float,
    current_score: float,
) -> str:
    """Build a breaking hotness alert message."""
    direction = "📈 飙升" if change_percent > 0 else "📉 骤降"
    plat_names = {
        "bilibili": "B站", "xiaohongshu": "小红书",
        "zhihu": "知乎", "github": "GitHub",
    }
    plat_display = plat_names.get(platform, platform)

    return (
        f"🚨 **热点异动告警**\n\n"
        f"主题: **{topic}**\n"
        f"平台: {plat_display}\n"
        f"变化: {direction} {change_percent:+.1f}%\n"
        f"当前热度: {current_score:.1f} 分\n"
    )
