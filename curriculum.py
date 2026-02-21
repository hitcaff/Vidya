# =============================================================================
# curriculum.py
# Loads curriculum content from .txt files based on subject and level.
#
# To add a new subject:
#   1. Create folder: curriculum/your_subject/
#   2. Add level0.txt, level1.txt etc with teaching content
#   3. That's it — no code changes needed
#
# Usage:
#   from curriculum import load_curriculum
#   content = load_curriculum("literacy", 0)
# =============================================================================

import os
from loguru import logger

CURRICULUM_DIR = os.path.join(os.path.dirname(__file__), "curriculum")


def load_curriculum(subject: str, level: int) -> str:
    """
    Loads curriculum content from a .txt file.

    Args:
        subject: e.g. "literacy", "numeracy", "life_skills"
        level:   0-4

    Returns:
        Curriculum text as a string.
        Falls back to level 0 if the requested level doesn't exist.
        Falls back to literacy level 0 if the subject doesn't exist.
    """
    # Try the exact file first
    path = _get_path(subject, level)

    if not os.path.exists(path):
        logger.warning(f"Curriculum not found: {path} — trying level 0")
        path = _get_path(subject, 0)

    if not os.path.exists(path):
        logger.warning(f"Subject not found: {subject} — falling back to literacy level 0")
        path = _get_path("literacy", 0)

    if not os.path.exists(path):
        logger.error("No curriculum files found at all!")
        return "Teach basic literacy — letters A, E, I, O, U and numbers 1 to 5."

    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    logger.info(f"Loaded curriculum: {subject}/level{level}")
    return content


def list_available_subjects() -> list:
    """Returns a list of all subjects that have curriculum files."""
    if not os.path.exists(CURRICULUM_DIR):
        return []
    return [
        d for d in os.listdir(CURRICULUM_DIR)
        if os.path.isdir(os.path.join(CURRICULUM_DIR, d))
    ]


def list_available_levels(subject: str) -> list:
    """Returns a list of available level numbers for a subject."""
    subject_dir = os.path.join(CURRICULUM_DIR, subject)
    if not os.path.exists(subject_dir):
        return []
    levels = []
    for f in os.listdir(subject_dir):
        if f.startswith("level") and f.endswith(".txt"):
            try:
                level_num = int(f.replace("level", "").replace(".txt", ""))
                levels.append(level_num)
            except ValueError:
                pass
    return sorted(levels)


def _get_path(subject: str, level: int) -> str:
    return os.path.join(CURRICULUM_DIR, subject, f"level{level}.txt")
