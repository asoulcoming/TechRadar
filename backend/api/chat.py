"""Chat endpoint — the main Agent interaction API."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.chat import ChatRequest, ChatResponse
from agent.graph import build_agent_graph
from agent.memory import ConversationMemory
from repository.posts import PostRepository
from repository.hotness import HotnessRepository
from collector.supervisor import CollectorSupervisor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Main Agent chat endpoint.

    Receives a user message, processes it through the LangGraph agent,
    and returns a structured response with optional chart data.
    """
    # Setup session
    memory = ConversationMemory(db)
    session_id = body.session_id or ConversationMemory.generate_session_id()

    # Setup repositories (per-request for MVP; use singleton in Phase 3+)
    post_repo = PostRepository(db)
    hotness_repo = HotnessRepository(db)
    supervisor = CollectorSupervisor(post_repo=post_repo)

    # Build agent graph with injected dependencies
    agent_graph = build_agent_graph(
        hotness_repo=hotness_repo,
        post_repo=post_repo,
        supervisor=supervisor,
    )

    # Build initial state (only serializable fields — no repo objects!)
    history = await memory.get_history(session_id)
    messages = history + [{"role": "user", "content": body.message}]

    config = {"configurable": {"thread_id": session_id}}
    state: dict = {
        "messages": messages,
        "user_input": body.message,
        "session_id": session_id,
    }

    # Run the agent graph
    try:
        result = await agent_graph.ainvoke(state, config)
    except Exception as e:
        logger.error(f"Agent execution error: {e}")
        return ChatResponse(
            reply=f"抱歉，处理你的请求时遇到了问题：{str(e)}。请稍后重试。",
            session_id=session_id,
        )

    # Build response
    reply = result.get("reply", "")
    chart_data = result.get("chart_data")
    sources = result.get("sources", [])

    # Save conversation to memory
    await memory.add_message(session_id, "user", body.message)
    await memory.add_message(session_id, "assistant", reply)

    # Clean up resources
    await supervisor.close()

    return ChatResponse(
        reply=reply,
        chart_data=chart_data,
        sources=sources,
        session_id=session_id,
    )
