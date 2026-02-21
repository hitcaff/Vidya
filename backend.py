# =============================================================================
# backend.py — Phase 4
# FastAPI server for Vidya.
# Added: WebSocket endpoint for visual learning signals.
#
# Run: py -3.11 -m uvicorn backend:app --reload --port 8000
# =============================================================================

import os
import uuid
from loguru import logger
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from visual_extractor import visual_channel

load_dotenv(override=True)

app = FastAPI(title="Vidya Backend", version="4.0.0")


# =============================================================================
# WebSocket — Visual Learning Channel
# Browser connects here to receive [SHOW:x] signals from Vidya
# =============================================================================

@app.websocket("/ws/visual/{session_id}")
async def visual_websocket(websocket: WebSocket, session_id: str):
    """
    Browser connects to this WebSocket at session start.
    When Vidya says [SHOW:letter_A], agent.py calls visual_channel.send_show()
    which pushes {"show": "letter_A"} here, and the browser displays the image.
    """
    await websocket.accept()
    visual_channel.register(session_id, websocket)
    logger.info(f"Visual WebSocket connected: {session_id}")

    try:
        while True:
            # Keep connection alive — browser sends pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        visual_channel.unregister(session_id)
        logger.info(f"Visual WebSocket disconnected: {session_id}")


# =============================================================================
# API Routes
# =============================================================================

@app.post("/api/session/start")
async def start_session():
    """
    Called by browser when student clicks Start.
    Returns session_id for the WebSocket visual channel.
    """
    session_id = str(uuid.uuid4())
    logger.info(f"New student session: {session_id}")
    return JSONResponse({
        "session_id": session_id,
        "ws_url": f"ws://localhost:8000/ws/visual/{session_id}",
        "status": "ready"
    })


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "Vidya Backend",
        "phase": 4,
        "sarvam_configured": bool(os.getenv("SARVAM_API_KEY")),
        "google_configured": bool(os.getenv("GOOGLE_API_KEY")),
    }


# =============================================================================
# Static files
# =============================================================================

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)
