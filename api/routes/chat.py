import json
import asyncio
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.schemas.chat import ChatRequest, ChatResponse
from agent.runner import run_agent, run_agent_stream

router = APIRouter()


@router.post("/chat")
async def chat(req: ChatRequest):
    conversation_id = req.conversation_id or str(uuid4())

    async def event_stream():
        async for token in run_agent_stream(req.question, req.user_id, conversation_id):
            data = json.dumps({"token": token})
            yield f"data: {data}\n\n"
        yield f"data: {json.dumps({'done': True, 'conversation_id': conversation_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/sync")
async def chat_sync(req: ChatRequest):
    conversation_id = req.conversation_id or str(uuid4())
    result = await asyncio.to_thread(run_agent, req.question, req.user_id, conversation_id)
    return ChatResponse(
        answer=result["answer"],
        sources=result.get("sources", []),
        tool=result.get("tool", "direct"),
    )
