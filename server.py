"""Entry point for cloud deployment (Render, etc.)."""

import uvicorn

if __name__ == "__main__":
    import os
    port = int(os.environ.get("API_PORT", os.environ.get("PORT", 10000)))
    uvicorn.run("api.app:app", host="0.0.0.0", port=port)
