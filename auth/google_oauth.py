"""Verify Google OAuth ID token from the frontend."""

import httpx


async def verify_google_token(id_token: str, client_id: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
            )
        if resp.status_code != 200:
            return None

        data = resp.json()
        if data.get("aud") != client_id:
            return None

        # Fix #2: Google may return email_verified as bool or string
        if str(data.get("email_verified", "false")).lower() != "true":
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
