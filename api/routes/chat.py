import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from api.schemas.chat import ChatRequest, ChatResponse
from api.dependencies import get_current_user
from agent.runner import run_agent, run_agent_stream

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat")
async def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    conversation_id = req.conversation_id or str(uuid4())
    user_id = user["id"]
    llm_provider = user.get("llm_provider")
    llm_model = user.get("llm_model")

    # Auto-title new conversations from the first message
    from storage.repositories import conversation_repo
    conv = conversation_repo.get_conversation(conversation_id)
    if not conv:
        title = req.question[:80] + ("..." if len(req.question) > 80 else "")
        conversation_repo.create_conversation(user_id, title=title, conversation_id=conversation_id)

    async def event_stream():
        try:
            async for token in run_agent_stream(
                req.question, user_id, conversation_id,
                llm_provider=llm_provider, llm_model=llm_model,
            ):
                data = json.dumps({"token": token})
                yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'done': True, 'conversation_id': conversation_id})}\n\n"
        except Exception as e:
            logger.error(f"Chat stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'token': f'Error: {e}'})}\n\n"
            yield f"data: {json.dumps({'done': True, 'conversation_id': conversation_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/sync")
async def chat_sync(req: ChatRequest, user: dict = Depends(get_current_user)):
    import asyncio
    conversation_id = req.conversation_id or str(uuid4())
    user_id = user["id"]
    llm_provider = user.get("llm_provider")
    llm_model = user.get("llm_model")
    try:
        result = await asyncio.to_thread(
            run_agent, req.question, user_id, conversation_id,
            llm_provider=llm_provider, llm_model=llm_model,
        )
        return ChatResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            tool=result.get("tool", "direct"),
        )
    except Exception as e:
        logger.error(f"Chat sync error: {e}", exc_info=True)
        return ChatResponse(answer=f"Error: {e}", sources=[], tool="direct")
