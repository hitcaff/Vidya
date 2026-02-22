# =============================================================================
# session_tracker.py
# Tracks what Vidya taught in each session and saves a summary to the DB.
#
# How it works:
# - Monitors the conversation during a session
# - Detects which concepts were covered (from [SHOW:x] signals + keywords)
# - When session ends, saves a summary to the DB
# - Next session, prompt_builder loads the summary and Vidya reviews it
#
# Usage:
#   from session_tracker import SessionTracker
#   tracker = SessionTracker(session_id)
#   tracker.record_visual(asset_key)       # called when [SHOW:x] fires
#   tracker.record_exchange(user, vidya)   # called after each turn
#   summary = await tracker.save()         # called on disconnect
# =============================================================================

import json
import re
from datetime import datetime
from loguru import logger
from db import DB_PATH
import aiosqlite


# Keywords that indicate a concept was taught
CONCEPT_PATTERNS = {
    "letter_A": ["letter a", "अक्षर a", "अक्षर अ", "letter_A"],
    "letter_E": ["letter e", "अक्षर e", "अक्षर ए", "letter_E"],
    "letter_I": ["letter i", "अक्षर i", "अक्षर इ", "letter_I"],
    "letter_O": ["letter o", "अक्षर o", "अक्षर ओ", "letter_O"],
    "letter_U": ["letter u", "अक्षर u", "अक्षर उ", "letter_U"],
    "counting_1_5":  ["one two three", "एक दो तीन", "ek do teen", "1 2 3"],
    "counting_6_10": ["six seven eight", "छह सात आठ", "6 7 8"],
    "counting_11_20":["eleven twelve", "ग्यारह बारह", "11 12"],
}


class SessionTracker:
    """
    Tracks a single session's teaching activity.
    Created at session start, saved at session end.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.started_at = datetime.now().isoformat()
        self.visuals_shown: list[str] = []       # All [SHOW:x] keys fired
        self.concepts_taught: list[str] = []     # Concepts detected as taught
        self.exchanges: list[dict] = []          # Full conversation turns
        self.student_successes: int = 0          # Times student got it right
        self.student_struggles: list[str] = []   # Concepts student found hard

    def record_visual(self, asset_key: str):
        """Called every time a [SHOW:x] tag fires."""
        if asset_key not in self.visuals_shown:
            self.visuals_shown.append(asset_key)
        # Map asset key to concept
        concept = self._asset_to_concept(asset_key)
        if concept and concept not in self.concepts_taught:
            self.concepts_taught.append(concept)
            logger.debug(f"Concept tracked: {concept}")

    def record_exchange(self, user_text: str, vidya_text: str):
        """Called after each conversation turn."""
        self.exchanges.append({
            "user": user_text,
            "vidya": vidya_text,
            "time": datetime.now().isoformat(),
        })
        # Detect success signals in Vidya's response
        success_words = ["बहुत अच्छे", "शाबाश", "great", "correct", "well done",
                         "excellent", "perfect", "बिल्कुल सही", "ਬਹੁਤ ਵਧੀਆ"]
        if any(w.lower() in vidya_text.lower() for w in success_words):
            self.student_successes += 1
        # Detect concepts from Vidya's text
        self._detect_concepts_from_text(vidya_text)

    def build_summary(self) -> str:
        """
        Builds a human-readable summary of the session.
        This is what Vidya reads at the start of the NEXT session.
        """
        if not self.concepts_taught and not self.visuals_shown:
            return "No specific concepts were covered — student was still in onboarding or warming up."

        concepts_str = ', '.join(self.concepts_taught) if self.concepts_taught else 'general introduction'
        visuals_str  = ', '.join(self.visuals_shown[:5]) if self.visuals_shown else 'none'
        exchanges    = len(self.exchanges)

        summary = (
            f"Last session covered: {concepts_str}. "
            f"Visual aids shown: {visuals_str}. "
            f"Student had {self.student_successes} successful responses "
            f"across {exchanges} exchanges. "
        )

        if self.student_struggles:
            summary += f"Student struggled with: {', '.join(self.student_struggles)}. "
            summary += "Review these concepts before introducing new ones."
        else:
            summary += "Student was engaged and responsive."

        return summary

    async def save(self) -> str:
        """
        Saves session summary to DB.
        Returns the summary string so agent.py can use it immediately.
        """
        summary = self.build_summary()
        ended_at = datetime.now().isoformat()

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO sessions (session_id, started_at, ended_at, summary, concepts_taught)
                VALUES (?, ?, ?, ?, ?)
            """, (
                self.session_id,
                self.started_at,
                ended_at,
                summary,
                json.dumps(self.concepts_taught),
            ))

            # Also update the user's last session summary and topics
            if self.concepts_taught:
                await db.execute("""
                    UPDATE users
                    SET topics_completed = json(
                        CASE
                            WHEN topics_completed IS NULL OR topics_completed = '[]'
                            THEN json_array()
                            ELSE topics_completed
                        END
                    )
                    WHERE session_id = ?
                """, (self.session_id,))

            await db.commit()

        logger.info(f"Session saved: {self.session_id} | concepts: {self.concepts_taught}")
        return summary

    async def load_last_summary(self) -> str | None:
        """
        Loads the most recent session summary for this student.
        Used by agent.py to build the teaching prompt.
        """
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("""
                SELECT summary FROM sessions
                WHERE session_id = ?
                ORDER BY started_at DESC
                LIMIT 1
            """, (self.session_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0]
                return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _asset_to_concept(self, asset_key: str) -> str | None:
        """Maps an asset key like 'letter_A' to a concept name."""
        if asset_key.startswith("letter_"):
            return f"Letter {asset_key.split('_')[1]}"
        if asset_key.startswith("number_"):
            return f"Number {asset_key.split('_')[1]}"
        if asset_key.startswith("vowel_"):
            return f"Vowel {asset_key.split('_')[1]}"
        return asset_key

    def _detect_concepts_from_text(self, text: str):
        """Scans Vidya's text for concept keywords."""
        text_lower = text.lower()
        for concept, patterns in CONCEPT_PATTERNS.items():
            if any(p.lower() in text_lower for p in patterns):
                readable = self._asset_to_concept(concept) or concept
                if readable not in self.concepts_taught:
                    self.concepts_taught.append(readable)
