# =============================================================================
# backend.py
# FastAPI server for Vidya.
#
# Phase 1 responsibilities:
#   - Serve the frontend (index.html + assets)
#   - Create Daily.co rooms and return their URL to the browser
#   - Health check endpoint
#
# Future phases will add:
#   - Phase 2: User profile + onboarding endpoints
#   - Phase 4: WebSocket endpoint for visual learning signals
#   - Phase 5: Progress and session tracking endpoints
#
# Run: uvicorn backend:app --reload --port 8000
# =============================================================================

import os
import uuid
import httpx
from loguru import logger
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv(override=True)

app = FastAPI(title="Vidya Backend", version="1.0.0")

# =============================================================================
# Daily.co room creation
# =============================================================================

DAILY_API_KEY = os.getenv("DAILY_API_KEY")
DAILY_API_URL = "https://api.daily.co/v1"


async def create_daily_room() -> dict:
    """
    Creates a temporary Daily.co room for one student session.
    The room expires after 1 hour automatically.

    Returns: { "url": "...", "name": "..." }
    """
    if not DAILY_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="DAILY_API_KEY not set in .env file"
        )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DAILY_API_URL}/rooms",
            headers={
                "Authorization": f"Bearer {DAILY_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "properties": {
                    "exp": int(__import__("time").time()) + 3600,  # 1 hour expiry
                    "max_participants": 2,                          # student + Vidya bot
                    "enable_chat": False,
                    "enable_screenshare": False,
                    "start_audio_off": False,
                    "start_video_off": True,                        # audio only — no video needed
                }
            }
        )

    if response.status_code != 200:
        logger.error(f"Daily room creation failed: {response.text}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not create Daily room: {response.text}"
        )

    return response.json()


# =============================================================================
# API Routes
# =============================================================================

class SessionResponse(BaseModel):
    room_url: str
    session_id: str
    room_name: str


@app.post("/api/session/start", response_model=SessionResponse)
async def start_session():
    """
    Called by the browser when the student clicks 'Start Learning'.
    Creates a Daily room and returns its URL for the browser to join.

    In Phase 2, this will also create or load the user's profile from the DB.
    In Phase 4, this will also initialise the WebSocket visual channel.
    """
    logger.info("New student session requested")

    room = await create_daily_room()
    session_id = str(uuid.uuid4())

    logger.info(f"Daily room created: {room['name']} | session: {session_id}")

    return SessionResponse(
        room_url=room["url"],
        session_id=session_id,
        room_name=room["name"],
    )


@app.get("/api/health")
async def health():
    """
    Simple health check — confirms the backend is running.
    Visit http://localhost:8000/api/health in your browser to verify.
    """
    return {
        "status": "ok",
        "service": "Vidya Backend",
        "phase": 1,
        "daily_configured": bool(DAILY_API_KEY),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "sarvam_configured": bool(os.getenv("SARVAM_API_KEY")),
    }


# =============================================================================
# Static files — serve the frontend
# =============================================================================

# Serve everything in frontend/ as static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def serve_frontend():
    """
    Serves the main frontend page.
    Visit http://localhost:8000 to see Vidya's browser UI.
    """
    return FileResponse("frontend/index.html")


# =============================================================================
# Future Phase 4 placeholder — WebSocket visual channel
# =============================================================================

# Phase 4 will add this:
#
# from fastapi import WebSocket
# active_visual_connections: dict[str, WebSocket] = {}
#
# @app.websocket("/ws/visual/{session_id}")
# async def visual_websocket(websocket: WebSocket, session_id: str):
#     await websocket.accept()
#     active_visual_connections[session_id] = websocket
#     try:
#         while True:
#             await websocket.receive_text()  # keep alive
#     except:
#         del active_visual_connections[session_id]
#
# async def send_visual_signal(session_id: str, asset_key: str):
#     ws = active_visual_connections.get(session_id)
#     if ws:
#         await ws.send_json({"show": asset_key})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)
