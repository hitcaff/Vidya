# =============================================================================
# visual_extractor.py
# Strips [SHOW:asset_key] tags from Vidya's text before TTS speaks it,
# and sends a visual signal to the browser via WebSocket.
#
# How it works:
#   Vidya says: "This is the letter A. [SHOW:letter_A]"
#   TTS hears:  "This is the letter A."         (tag removed)
#   Browser receives: {"show": "letter_A"}      (via WebSocket)
#   Image card shows: /assets/letter_A.svg
#
# Usage in agent.py:
#   from visual_extractor import extract_visuals
#   clean_text, asset_key = extract_visuals(text)
# =============================================================================

import re
from loguru import logger

# Pattern matches [SHOW:anything] anywhere in text
SHOW_PATTERN = re.compile(r'\[SHOW:([^\]]+)\]')


def extract_visuals(text: str) -> tuple[str, list[str]]:
    """
    Extracts all [SHOW:x] tags from text.

    Returns:
        (clean_text, asset_keys)
        clean_text  — text with all [SHOW:x] tags removed (for TTS)
        asset_keys  — list of asset keys to display (for WebSocket)

    Example:
        "This is letter A. [SHOW:letter_A] Say Aaa!"
        → ("This is letter A. Say Aaa!", ["letter_A"])
    """
    asset_keys = SHOW_PATTERN.findall(text)
    clean_text = SHOW_PATTERN.sub('', text).strip()

    # Clean up any double spaces left after tag removal
    clean_text = re.sub(r'  +', ' ', clean_text)

    if asset_keys:
        logger.debug(f"Visual signals extracted: {asset_keys}")

    return clean_text, asset_keys


# =============================================================================
# WebSocket connection registry
# Stores active WebSocket connections by session_id
# Used by backend.py to push visual signals to the browser
# =============================================================================

class VisualChannel:
    """
    Registry of active WebSocket connections.
    Shared between backend.py (which registers connections)
    and agent.py (which sends signals).
    """
    def __init__(self):
        self._connections: dict = {}

    def register(self, session_id: str, websocket):
        self._connections[session_id] = websocket
        logger.info(f"Visual channel registered: {session_id}")

    def unregister(self, session_id: str):
        if session_id in self._connections:
            del self._connections[session_id]
            logger.info(f"Visual channel unregistered: {session_id}")

    async def send_show(self, session_id: str, asset_key: str):
        ws = self._connections.get(session_id)
        if ws:
            try:
                await ws.send_json({"show": asset_key})
                logger.debug(f"Visual signal sent: {asset_key} → {session_id}")
            except Exception as e:
                logger.warning(f"Failed to send visual signal: {e}")
                self.unregister(session_id)

    async def send_hide(self, session_id: str):
        ws = self._connections.get(session_id)
        if ws:
            try:
                await ws.send_json({"hide": True})
            except Exception as e:
                logger.warning(f"Failed to send hide signal: {e}")


# Global instance — imported by both backend.py and agent.py
visual_channel = VisualChannel()
