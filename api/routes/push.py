"""Web Push / PWA notification routes."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies import get_current_user
from configs.config import settings
from storage.repositories import push_repo

router = APIRouter(prefix="/push")
logger = logging.getLogger(__name__)


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict  # {"p256dh": "...", "auth": "..."}


@router.get("/vapid-public-key")
def get_vapid_public_key():
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(503, "Push notifications not configured (missing VAPID keys)")
    return {"publicKey": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe")
def subscribe(body: PushSubscription, user: dict = Depends(get_current_user)):
    p256dh = body.keys.get("p256dh", "")
    auth = body.keys.get("auth", "")
    if not p256dh or not auth:
        raise HTTPException(400, "Missing p256dh or auth keys")
    sub = push_repo.save_subscription(user["id"], body.endpoint, p256dh, auth)
    return {"status": "subscribed", "id": sub["id"]}


@router.delete("/subscribe")
def unsubscribe(body: PushSubscription, user: dict = Depends(get_current_user)):
    push_repo.delete_subscription(user["id"], body.endpoint)
    return {"status": "unsubscribed"}


def send_push_notification(endpoint: str, p256dh: str, auth: str, payload: dict) -> bool:
    """Send a single Web Push notification. Returns True on success."""
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        return False
    try:
        from pywebpush import webpush, WebPushException
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_CLAIMS_EMAIL},
        )
        return True
    except Exception as e:
        logger.warning(f"Push failed for {endpoint[:40]}: {e}")
        return False
