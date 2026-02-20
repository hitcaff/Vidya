# =============================================================================
# backend.py
# FastAPI server for Vidya.
#
# Updated: Removed Daily.co — now uses Pipecat's built-in WebRTC transport.
# The frontend connects directly to the Pipecat agent via WebRTC.
#
# Run: uvicorn backend:app --reload --port 8000
# =============================================================================

import os
import uuid
from loguru import logger
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

load_dotenv(override=True)

app = FastAPI(title="Vidya Backend", version="1.0.0")


# =============================================================================
# API Routes
# =============================================================================

@app.post("/api/session/start")
async def start_session():
    """
    Called by the browser when the student clicks 'Start Learning'.
    Returns a session ID — the frontend connects directly to the
    Pipecat WebRTC agent.

    In Phase 2 this will also create/load the user profile from DB.
    """
    session_id = str(uuid.uuid4())
    logger.info(f"New student session: {session_id}")

    return JSONResponse({
        "session_id": session_id,
        "agent_url": "http://localhost:8000",
        "status": "ready"
    })


@app.get("/api/health")
async def health():
    """
    Health check — visit http://localhost:8000/api/health to verify setup.
    """
    return {
        "status": "ok",
        "service": "Vidya Backend",
        "phase": 1,
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "sarvam_configured": bool(os.getenv("SARVAM_API_KEY")),
    }


# =============================================================================
# Static files — serve the frontend
# =============================================================================

app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)
