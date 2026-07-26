"""Vercel Python entrypoint — re-export the FastAPI app.

Long-running FastAPI + in-memory sessions are a soft fit for serverless;
see docs/vercel-deploy.md. HTTP chat + static UI work; Chirp WebSocket STT
and durable local disk do not.
"""

from tutor.web_app import app  # noqa: F401
