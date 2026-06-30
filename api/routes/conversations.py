from fastapi import APIRouter, HTTPException, Depends

from api.dependencies import get_current_user
from storage.repositories import conversation_repo

router = APIRouter(prefix="/conversations")


@router.get("")
def list_conversations(limit: int = 30, offset: int = 0, user: dict = Depends(get_current_user)):
    convos = conversation_repo.list_conversations(user["id"], limit=limit, offset=offset)
    return convos


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, user: dict = Depends(get_current_user)):
    conv = conversation_repo.get_conversation(conversation_id)
    if not conv or conv["user_id"] != user["id"]:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.get("/{conversation_id}/messages")
def get_messages(conversation_id: str, limit: int = 50, user: dict = Depends(get_current_user)):
    conv = conversation_repo.get_conversation(conversation_id)
    if not conv or conv["user_id"] != user["id"]:
        raise HTTPException(404, "Conversation not found")
    return conversation_repo.get_messages(conversation_id, limit=limit)


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, user: dict = Depends(get_current_user)):
    conv = conversation_repo.get_conversation(conversation_id)
    if not conv or conv["user_id"] != user["id"]:
        raise HTTPException(404, "Conversation not found")
    conversation_repo.delete_conversation(conversation_id)
    return {"status": "deleted"}
