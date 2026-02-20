# =============================================================================
# db.py
# SQLite database for Vidya — user profiles and progress tracking.
#
# Phase 2: Creates and manages the users table.
# Future phases will add: sessions, progress, quiz_scores tables.
#
# Usage:
#   from db import init_db, get_user, save_user, update_progress
# =============================================================================

import json
import aiosqlite
from loguru import logger
from datetime import datetime

DB_PATH = "vidya.db"


# =============================================================================
# Database initialisation — run once at startup
# =============================================================================

async def init_db():
    """
    Creates the database and all tables if they don't exist.
    Safe to call every time the app starts.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT UNIQUE NOT NULL,
                name            TEXT,
                preferred_language  TEXT DEFAULT 'unknown',
                literacy_level  INTEGER DEFAULT 0,
                numeracy_level  INTEGER DEFAULT 0,
                school_attended TEXT DEFAULT 'unknown',
                learning_goal   TEXT,
                learning_path   TEXT DEFAULT '["literacy"]',
                current_subject TEXT DEFAULT 'literacy',
                current_level   INTEGER DEFAULT 0,
                topics_completed TEXT DEFAULT '[]',
                quiz_scores     TEXT DEFAULT '[]',
                total_stars     INTEGER DEFAULT 0,
                session_count   INTEGER DEFAULT 0,
                last_seen       TEXT,
                created_at      TEXT,
                onboarding_done INTEGER DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT NOT NULL,
                started_at      TEXT,
                ended_at        TEXT,
                summary         TEXT,
                concepts_taught TEXT DEFAULT '[]'
            )
        """)

        await db.commit()
        logger.info("Database initialised at vidya.db")


# =============================================================================
# User profile functions
# =============================================================================

async def get_user(session_id: str) -> dict | None:
    """
    Loads a user profile by session_id.
    Returns None if this is a new user.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE session_id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None

            user = dict(row)
            # Parse JSON fields
            user["learning_path"]     = json.loads(user["learning_path"] or '["literacy"]')
            user["topics_completed"]  = json.loads(user["topics_completed"] or '[]')
            user["quiz_scores"]       = json.loads(user["quiz_scores"] or '[]')
            return user


async def save_user(session_id: str, profile: dict) -> dict:
    """
    Creates a new user profile in the database.
    Called after onboarding is complete.
    """
    now = datetime.now().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (
                session_id, name, preferred_language, literacy_level,
                numeracy_level, school_attended, learning_goal,
                learning_path, current_subject, current_level,
                session_count, last_seen, created_at, onboarding_done
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            profile.get("name", "Friend"),
            profile.get("preferred_language", "unknown"),
            profile.get("literacy_level", 0),
            profile.get("numeracy_level", 0),
            profile.get("school_attended", "unknown"),
            profile.get("learning_goal", "literacy"),
            json.dumps(profile.get("learning_path", ["literacy"])),
            profile.get("current_subject", "literacy"),
            profile.get("current_level", 0),
            1,
            now,
            now,
            1,
        ))
        await db.commit()

    logger.info(f"User saved: {profile.get('name')} | lang: {profile.get('preferred_language')} | level: {profile.get('literacy_level')}")
    return await get_user(session_id)


async def update_session_count(session_id: str):
    """
    Increments the session counter and updates last_seen.
    Called at the start of every session.
    """
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users
            SET session_count = session_count + 1,
                last_seen = ?
            WHERE session_id = ?
        """, (now, session_id))
        await db.commit()


async def add_stars(session_id: str, count: int = 1):
    """
    Adds stars to the user's total. Called when a student gets something right.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users
            SET total_stars = total_stars + ?
            WHERE session_id = ?
        """, (count, session_id))
        await db.commit()


async def mark_topic_complete(session_id: str, topic: str):
    """
    Marks a topic as complete in the user's progress.
    """
    user = await get_user(session_id)
    if not user:
        return

    topics = user["topics_completed"]
    if topic not in topics:
        topics.append(topic)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET topics_completed = ? WHERE session_id = ?
        """, (json.dumps(topics), session_id))
        await db.commit()


async def update_level(session_id: str, subject: str, level: int):
    """
    Updates the user's current subject and level.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users
            SET current_subject = ?,
                current_level = ?
            WHERE session_id = ?
        """, (subject, level, session_id))
        await db.commit()
