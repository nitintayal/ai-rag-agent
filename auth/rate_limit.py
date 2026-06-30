"""Simple in-memory rate limiter — shared across auth endpoints (register, login, password reset)."""

import time
from collections import defaultdict

from fastapi import HTTPException, Request

_attempts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 5
_RATE_WINDOW = 60


def check_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    _attempts[ip] = [t for t in _attempts[ip] if now - t < _RATE_WINDOW]
    if len(_attempts[ip]) >= _RATE_LIMIT:
        raise HTTPException(429, "Too many attempts. Try again in a minute.")
    _attempts[ip].append(now)
