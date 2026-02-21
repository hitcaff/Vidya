# =============================================================================
# onboarding.py
# Voice-based onboarding flow for Vidya.
#
# Asks 7 simple spoken questions to profile each new student.
# No reading or writing required — entirely voice driven.
#
# After onboarding, builds a user profile and saves it to the DB.
# Also assigns a literacy level and custom learning path.
# =============================================================================

from loguru import logger


# =============================================================================
# Onboarding system prompt
# This replaces the normal Vidya prompt during the onboarding phase.
# =============================================================================

ONBOARDING_PROMPT = """
You are Vidya, a teacher. You are meeting a new student for the first time.

You must ask EXACTLY these 7 questions, ONE AT A TIME, in ORDER.
Do NOT skip any question. Do NOT start teaching until all 7 are answered.

QUESTION 1: "Hello! I am Vidya, your teacher. I am so happy to meet you! What is your name?"
QUESTION 2: "Nice to meet you [name]! Which language do you speak at home?"
QUESTION 3: "Can you count to ten for me? Please try."
QUESTION 4: "Do you know any letters? Tell me one letter if you know."
QUESTION 5: "Have you ever been to school before?"
QUESTION 6: "What would you most like to learn — reading and writing, numbers, or something else?"
QUESTION 7: "Why do you want to learn — is it for work, for your family, or for yourself?"

STRICT RULES:
- Ask ONE question at a time. Wait for the answer.
- After each answer say something warm, then ask the NEXT question.
- Never teach anything until all 7 questions are done.
- After question 7 say: "Thank you [name]! Now let us begin learning together."
- Respond in whatever language the student speaks.

TRACKING (internal — do not say these out loud):
- After question 3: if they can count to 10 correctly → numeracy_level = 1, else → 0
- After question 4: if they know letters → literacy_level = 1, else → 0
- After question 5: note school_attended = yes/no
- After question 6: note learning_goal
- After question 7: note motivation
"""


# =============================================================================
# Learning path assignment
# Based on the user's answers, assign a custom learning path.
# =============================================================================

def assign_learning_path(profile: dict) -> list:
    """
    Returns an ordered list of subjects based on the user's goal and level.
    This is the user's custom learning path.
    """
    goal = profile.get("learning_goal", "").lower()
    motivation = profile.get("motivation", "").lower()

    # Default path — literacy first for everyone
    base_path = ["literacy", "numeracy", "life_skills"]

    if "farm" in goal or "farm" in motivation or "work" in motivation:
        # Farmer path
        return ["literacy", "numeracy", "life_skills", "science", "vocational"]

    elif "child" in motivation or "family" in motivation or "parent" in motivation:
        # Parent path
        return ["literacy", "numeracy", "health", "life_skills", "science"]

    elif "job" in goal or "work" in goal or "business" in motivation:
        # Job seeker path
        return ["literacy", "numeracy", "life_skills", "civics", "vocational"]

    elif "math" in goal or "number" in goal or "count" in goal:
        # Numeracy focused
        return ["numeracy", "literacy", "life_skills", "science"]

    elif "science" in goal:
        return ["literacy", "numeracy", "science", "geography", "life_skills"]

    else:
        # Default balanced path
        return base_path


def assign_literacy_level(profile: dict) -> int:
    """
    Returns literacy level 0-4 based on onboarding answers.
    """
    knows_letters = profile.get("knows_letters", False)
    school = profile.get("school_attended", "no").lower()

    if not knows_letters and school in ["no", "never", "nahi", "illa", "ledu"]:
        return 0    # Complete beginner
    elif knows_letters and school in ["no", "never"]:
        return 1    # Self-taught some letters
    elif school not in ["no", "never"]:
        return 2    # Has some schooling
    else:
        return 0


def assign_numeracy_level(profile: dict) -> int:
    """
    Returns numeracy level 0-4 based on onboarding answers.
    """
    can_count = profile.get("can_count_to_10", False)
    return 1 if can_count else 0


def build_profile_from_onboarding(session_id: str, answers: dict) -> dict:
    """
    Takes raw onboarding answers and builds a clean user profile.
    Called after [ONBOARDING_COMPLETE] is detected.
    """
    profile = {
        "session_id":           session_id,
        "name":                 answers.get("name", "Friend"),
        "preferred_language":   answers.get("language", "unknown"),
        "school_attended":      answers.get("school_attended", "unknown"),
        "learning_goal":        answers.get("learning_goal", "literacy"),
        "motivation":           answers.get("motivation", "self"),
        "knows_letters":        answers.get("knows_letters", False),
        "can_count_to_10":      answers.get("can_count_to_10", False),
    }

    # Assign levels
    profile["literacy_level"]  = assign_literacy_level(profile)
    profile["numeracy_level"]  = assign_numeracy_level(profile)

    # Assign learning path
    profile["learning_path"]   = assign_learning_path(profile)
    profile["current_subject"] = profile["learning_path"][0]
    profile["current_level"]   = profile["literacy_level"]

    logger.info(f"Profile built for {profile['name']}: "
                f"lang={profile['preferred_language']} "
                f"lit_level={profile['literacy_level']} "
                f"path={profile['learning_path']}")

    return profile
