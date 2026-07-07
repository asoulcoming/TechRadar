"""LangGraph Agent workflow.

Defines the state graph for processing user queries about tech trends.
The agent: parses intent → plans tasks → calls tools → generates response.

Dependencies (repos, supervisor) are injected at graph build time via closures,
NOT passed through state (which must be msgpack-serializable).
"""

from __future__ import annotations

import logging
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agent.tools import (
    search_topic_hotness,
    trigger_collection,
    get_top_topics,
    compare_topics,
)

logger = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    """State flowing through the LangGraph (must be msgpack-serializable)."""
    messages: list[dict]           # Conversation history
    user_input: str                # Latest user message
    intent: dict                   # Parsed intent: {action, topic, platforms, days}
    tool_results: list[dict]       # Results from tool calls
    reply: str                     # Final response
    chart_data: Optional[dict]     # Chart data for frontend
    sources: list[dict]            # Source references
    session_id: str                # Session ID


# ─── Graph Node Functions ─────────────────────────────────────────────

def _make_parse_intent():
    """Create parse_intent node (no external deps needed)."""
    def parse_intent(state: AgentState) -> AgentState:
        msg = state.get("user_input", "")
        msg_lower = msg.lower()

        intent = {"action": "general"}

        if any(w in msg_lower for w in ["热度", "趋势", "怎么样", "最近", "趋势图"]):
            intent["action"] = "trend_query"
        elif any(w in msg_lower for w in ["最火", "热门", "top", "排行", "哪些"]):
            intent["action"] = "top_topics"
        elif any(w in msg_lower for w in ["对比", "比较", "vs", "哪个更"]):
            intent["action"] = "compare"
        elif any(w in msg_lower for w in ["查一下", "搜索", "采集", "最新"]):
            intent["action"] = "trigger_collect"
        elif any(w in msg_lower for w in ["日报", "报告", "总结"]):
            intent["action"] = "daily_report"

        for topic_hint in ["GEO", "Rust", "Python", "Go", "大模型", "AI", "LangChain",
                            "Kubernetes", "Docker", "React", "Vue", "TypeScript",
                            "Java", "C++", "Zig", "Redis", "PostgreSQL"]:
            if topic_hint.lower() in msg_lower or topic_hint in msg:
                intent["topic"] = topic_hint
                break

        for plat_hint, plat_name in [
            ("b站", "bilibili"), ("bilibili", "bilibili"),
            ("小红书", "xiaohongshu"), ("知乎", "zhihu"),
            ("github", "github"),
        ]:
            if plat_hint.lower() in msg_lower:
                intent["platforms"] = intent.get("platforms", []) + [plat_name]

        if "platforms" not in intent or not intent["platforms"]:
            intent["platforms"] = ["bilibili", "xiaohongshu", "zhihu", "github"]

        if "一周" in msg or "7天" in msg or "week" in msg_lower:
            intent["days"] = 7
        elif "一个月" in msg or "30天" in msg or "month" in msg_lower:
            intent["days"] = 30
        elif "昨天" in msg or "今天" in msg or "一天" in msg:
            intent["days"] = 1
        else:
            intent["days"] = 7

        state["intent"] = intent
        logger.info(f"Parsed intent: {intent}")
        return state
    return parse_intent


def _make_execute_tools(hotness_repo, post_repo, supervisor):
    """Create execute_tools node with injected dependencies."""
    async def execute_tools(state: AgentState) -> AgentState:
        intent = state.get("intent", {})
        action = intent.get("action", "general")
        tool_results = []

        try:
            if action == "trend_query":
                topic = intent.get("topic", "")
                platforms = ",".join(intent.get("platforms", []))
                days = intent.get("days", 7)
                if topic:
                    result = await search_topic_hotness(
                        topic=topic, platforms=platforms, days=days,
                        hotness_repo=hotness_repo, post_repo=post_repo,
                    )
                    tool_results.append(result)

            elif action == "top_topics":
                for plat in intent.get("platforms", ["github"])[:1]:
                    result = await get_top_topics(
                        platform=plat, limit=10, hotness_repo=hotness_repo,
                    )
                    tool_results.append(result)

            elif action == "compare":
                topic = intent.get("topic", "")
                platform = intent.get("platforms", ["bilibili"])[0]
                if topic:
                    result = await compare_topics(
                        topics=topic, platform=platform,
                        days=intent.get("days", 7),
                        hotness_repo=hotness_repo,
                    )
                    tool_results.append(result)

            elif action == "trigger_collect":
                topic = intent.get("topic", "")
                platforms = ",".join(intent.get("platforms", []))
                if topic:
                    result = await trigger_collection(
                        topic=topic, platforms=platforms, supervisor=supervisor,
                    )
                    tool_results.append(result)

            elif action == "daily_report":
                tool_results.append({
                    "action": "daily_report",
                    "message": "日报生成功能由定时任务自动触发。手动生成请调用 /api/reports/generate",
                })

            else:
                result = await get_top_topics(
                    platform="github", limit=5, hotness_repo=hotness_repo,
                )
                tool_results.append(result)

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            tool_results.append({"error": str(e)})

        state["tool_results"] = tool_results
        return state
    return execute_tools


def _make_generate_response():
    """Create generate_response node (no external deps needed)."""
    def generate_response(state: AgentState) -> AgentState:
        intent = state.get("intent", {})
        tool_results = state.get("tool_results", [])

        reply_parts = []
        chart_data = None
        sources = []

        for result in tool_results:
            if "error" in result:
                reply_parts.append(f"查询时遇到问题: {result['error']}\n")
                continue

            if "topic" in result and "platforms" in result:
                topic = result["topic"]
                plat_data = result.get("platforms", {})
                reply_parts.append(f"## 🔍 {topic} 热度分析\n\n")
                for plat, data in plat_data.items():
                    if "error" in data:
                        reply_parts.append(f"- **{plat}**: 数据暂不可用\n")
                    else:
                        reply_parts.append(
                            f"- **{plat}**: {data.get('trend', 'N/A')} "
                            f"(变化: {data.get('change_percent', 0)}%, "
                            f"数据点: {data.get('data_points', 0)})\n"
                        )

                if result.get("top_posts"):
                    reply_parts.append("\n### 热门内容\n")
                    for post in result["top_posts"]:
                        reply_parts.append(f"- [{post['platform']}] {post['title']}\n")
                        sources.append(post)

                chart_data = {
                    "type": "line",
                    "title": f"{topic} 热度趋势",
                    "xAxis": [],
                    "series": [],
                }

            elif "topics" in result:
                topics = result.get("topics", [])
                reply_parts.append(f"## 📊 {result.get('platform', '')} 当前热门技术主题\n\n")
                for i, t in enumerate(topics, 1):
                    reply_parts.append(f"{i}. **{t['topic']}** — {t['avg_score']}分\n")

            elif "action" in result:
                reply_parts.append(f"{result.get('message', '')}\n")

        if not reply_parts:
            reply_parts.append(
                "你好！我是 AI 热点洞察助手。我可以帮你：\n"
                "- 查询技术主题的热度趋势（例如：「GEO 最近一周热度如何？」）\n"
                "- 查看各平台热门技术话题排行\n"
                "- 对比不同技术主题的热度\n"
                "- 查看技术热点日报\n\n"
                "请问你有什么想了解的技术话题？"
            )

        state["reply"] = "".join(reply_parts)
        state["chart_data"] = chart_data
        state["sources"] = sources
        return state
    return generate_response


# ─── Graph Construction ───────────────────────────────────────────────

def build_agent_graph(hotness_repo=None, post_repo=None, supervisor=None):
    """Build and compile the LangGraph agent workflow.

    Dependencies are injected at build time via closures, so the graph
    state remains msgpack-serializable for checkpointer support.
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("parse_intent", _make_parse_intent())
    workflow.add_node("execute_tools", _make_execute_tools(hotness_repo, post_repo, supervisor))
    workflow.add_node("generate_response", _make_generate_response())

    workflow.set_entry_point("parse_intent")
    workflow.add_edge("parse_intent", "execute_tools")
    workflow.add_edge("execute_tools", "generate_response")
    workflow.add_edge("generate_response", END)

    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    return app
