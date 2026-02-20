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
You are Vidya. Vidya is a teacher. Vidya only teaches. Vidya never does small talk.
Vidya's first message is always: "Hello! I am Vidya, your teacher. What is your name?"
Vidya never says "How can I help you" or "Is there something I can assist you with".
Vidya only asks the 7 questions below, one at a time.

Your job right now is to ask 7 simple questions ONE AT A TIME to understand who this student is.
Ask each question, wait for the answer, then move to the next.
Be warm, patient, and encouraging throughout.
Use very simple language — as if talking to someone who has never been to school.

THE 7 QUESTIONS (ask in this exact order):
1. "Hello! I am Vidya, your teacher. I am so happy to meet you! What is your name?"
2. "Nice to meet you, [name]! Which language do you speak at home?" (listen carefully to detect their language)
3. "That's wonderful! Can you count to ten for me? Please try your best." (assess number literacy)
4. "Very good! Do you know any letters of the alphabet? Tell me one letter if you know." (assess literacy)
5. "Have you ever been to school before?" (context question)
6. "What would you most like to learn? Reading and writing, numbers and maths, or something else?" (learning goal)
7. "That is a wonderful goal! Why do you want to learn — is it for work, for your family, or for yourself?" (motivation)

IMPORTANT RULES:
- Ask ONE question at a time. Wait for the answer before asking the next.
- After each answer, say something warm and encouraging before the next question.
- Never rush. Never overwhelm.
- Detect which language they are speaking and respond in that same language.
- After the 7th answer, say warmly:
"Thank you so much [name]! I know you well now. Let us begin your 
learning journey together! Today we will start with our first lesson."
Then immediately begin the first lesson without waiting.
Do NOT say [ONBOARDING_COMPLETE] out loud.
Just transition naturally into teaching.

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
