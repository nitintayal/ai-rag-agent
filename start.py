"""Cloud entry point with error logging."""

import os
import sys
import traceback

# Ensure project root is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", os.environ.get("API_PORT", "10000")))
    print(f"Starting on port {port}", flush=True)
    print(f"Python: {sys.version}", flush=True)
    print(f"CWD: {os.getcwd()}", flush=True)
    print(f"Files: {os.listdir('.')}", flush=True)

    try:
        import uvicorn
        uvicorn.run("api.app:app", host="0.0.0.0", port=port)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
