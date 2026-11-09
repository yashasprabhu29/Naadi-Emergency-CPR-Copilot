"""Run the backend for local development.

Reloads when backend code or the project's .env file changes, so a newly
pasted GNANI_API_KEY takes effect without a manual restart.

Run from the project root:  python -m backend.scripts.dev_server
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["backend", "."],
        reload_includes=["*.py", ".env"],
        reload_excludes=["frontend/*", "data/*", ".venv/*", "audio/*"],
    )
