"""Verify Google OAuth ID token from the frontend."""

import httpx


async def verify_google_token(id_token: str, client_id: str) -> dict | None:
    """Verify a Google ID token and return user info.

    Returns dict with: sub, email, name, picture, email_verified
    Returns None if invalid.
    """
    try:
        resp = httpx.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}",
            timeout=10,
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        if data.get("aud") != client_id:
            return None

        if not data.get("email_verified", "false") == "true":
            return None

        email = data["email"]

        # Build display name: prefer full name, then given+family, then email prefix
        name = data.get("name", "").strip()
        if not name or name == email:
            given = data.get("given_name", "").strip()
            family = data.get("family_name", "").strip()
            name = f"{given} {family}".strip()
        if not name or name == email:
            name = email.split("@")[0]

        return {
            "sub": data["sub"],
            "email": email,
            "name": name,
            "picture": data.get("picture", ""),
        }
    except Exception:
        return None
