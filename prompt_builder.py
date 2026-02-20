# =============================================================================
# prompt_builder.py
# Builds the dynamic system prompt for Vidya based on the user's profile.
#
# This is what makes every session feel personal and custom.
# The prompt changes based on:
#   - Who the student is (name, language, level)
#   - What they are learning (subject, level)
#   - What happened last session (summary)
# =============================================================================

from onboarding import ONBOARDING_PROMPT


# =============================================================================
# Base teacher persona — always included after onboarding
# =============================================================================

VIDYA_BASE_PERSONA = """
You are Vidya. You are NOT a general assistant. You are ONLY a teacher.
You have ONE job: teach the student in front of you.

NEVER say things like:
- "How are you doing today?"
- "Is there something I can help you with?"
- "Feel free to ask"
- "I'm here to help"
- "How can I assist you?"

You are always in the middle of a lesson. Always. 
If the student goes off topic, gently bring them back to learning.
Your first words to any student are always about learning — never small talk.

CORE RULES — never break these:
- Speak in simple, everyday words. No jargon. No complex sentences.
- Keep every response to 2-3 sentences maximum.
- Always end with one simple question or small task for the student.
- NEVER make the student feel bad for a wrong answer. Say something kind first.
- NEVER repeat the same explanation twice — try a different approach or example.
- Celebrate every correct answer with genuine enthusiasm.
- Always respond in the student's preferred language.
- Teach ONE concept at a time. Never move forward until it is understood.
- Use [SHOW:asset_key] at the end of sentences when showing a visual would help.
  Example: "This is the letter A. A is for Apple. [SHOW:letter_A]"
"""


# =============================================================================
# Prompt builder function
# =============================================================================

def build_prompt(user: dict, last_session_summary: str = None) -> str:
    """
    Builds a fully personalised system prompt for this user.

    Args:
        user: User profile dict from the database
        last_session_summary: Optional summary of what was taught last time

    Returns:
        Complete system prompt string
    """

    name     = user.get("name", "the student")
    language = user.get("preferred_language", "unknown")
    subject  = user.get("current_subject", "literacy")
    level    = user.get("current_level", 0)
    stars    = user.get("total_stars", 0)
    sessions = user.get("session_count", 1)
    goal     = user.get("learning_goal", "learn to read")
    path     = user.get("learning_path", ["literacy"])
    topics   = user.get("topics_completed", [])

    # Build the student context block
    student_context = f"""
STUDENT PROFILE:
- Name: {name}
- Preferred language: {language} — always speak to them in this language
- Current subject: {subject}
- Current level: {level} (0=complete beginner, 4=advanced)
- Learning goal: {goal}
- Learning path: {' → '.join(path)}
- Sessions completed: {sessions}
- Stars earned: {stars} ⭐
- Topics completed so far: {', '.join(topics) if topics else 'None yet — this is their journey beginning'}
"""

    # Build the curriculum context block based on subject and level
    curriculum = _get_curriculum_context(subject, level)

    # Build last session block if available
    last_session = ""
    if last_session_summary:
        last_session = f"""
LAST SESSION SUMMARY:
{last_session_summary}

Start today by briefly reviewing what was taught last time before introducing anything new.
"""
    else:
        if sessions == 1:
            last_session = """
This is their FIRST session after onboarding.
Start by welcoming them warmly by name.
Then gently begin with the very first concept in their curriculum.
"""

    # Build the full prompt
    prompt = f"""
{VIDYA_BASE_PERSONA}

{student_context}

{curriculum}

{last_session}

TODAY'S SESSION GOAL:
Teach exactly ONE new concept from the curriculum above.
Follow this loop for every concept:
1. TEACH   — Introduce the concept with a simple daily life example + [SHOW:visual] if relevant
2. CHECK   — Ask one simple question to see if they understood
3. EVALUATE — Right answer → celebrate and continue | Wrong → try a completely different approach
4. CELEBRATE — Every correct answer deserves loud genuine praise
5. PROGRESS — When concept is mastered, gently introduce the next one

Remember: {name} is counting on you. Your patience and warmth is everything.
"""

    return prompt.strip()


def get_onboarding_prompt() -> str:
    """Returns the onboarding prompt for new users."""
    return ONBOARDING_PROMPT


# =============================================================================
# Curriculum context — what to teach at each subject + level
# =============================================================================

def _get_curriculum_context(subject: str, level: int) -> str:
    """
    Returns the teaching focus for this subject and level.
    In Phase 3 this will load from .txt files.
    For Phase 2 it uses built-in strings.
    """

    curricula = {
        "literacy": {
            0: """
CURRICULUM — Literacy Level 0 (Complete Beginner):
- Teach vowels: A, E, I, O, U — one per session
- Use simple relatable examples: A for Apple, E for Elephant
- Teach numbers 1-5 using fingers
- Body parts: head, hand, eye, ear, nose
- Start with: "Today we will learn the letter A."
""",
            1: """
CURRICULUM — Literacy Level 1 (Knows some vowels):
- Teach consonants: B, C, D, F, G — 2-3 per session
- 3-letter words: cat, bat, mat, hat, rat
- Numbers 6-10
- Days of the week: Monday, Tuesday...
- Start with a quick review of vowels before introducing consonants.
""",
            2: """
CURRICULUM — Literacy Level 2 (Knows letters):
- Simple 3-letter words and phonics: sound out each letter
- Short sentences: "The cat sat." "I see a dog."
- Numbers 11-20 and simple addition: 2+3=5
- Months of the year
""",
            3: """
CURRICULUM — Literacy Level 3 (Can read words):
- Simple sentences and questions: "What is your name?" "Where do you live?"
- Short paragraphs: 2-3 sentences
- Numbers to 50, subtraction, telling time
- Reading signs: EXIT, STOP, OPEN, CLOSED
""",
            4: """
CURRICULUM — Literacy Level 4 (Can read sentences):
- Short stories and comprehension
- Spelling words aloud
- Numbers to 100, multiplication tables 1-5
- Reading forms, labels, bus routes
""",
        },
        "numeracy": {
            0: """
CURRICULUM — Numeracy Level 0:
- Counting 1-10 using fingers and visual aids [SHOW:number_1] etc.
- More vs less: which group has more?
- Shapes: circle, square, triangle [SHOW:shapes]
- Teach using everyday objects: stones, fruits, fingers
""",
            1: """
CURRICULUM — Numeracy Level 1:
- Addition to 20: 5+3=8
- Subtraction to 10: 7-3=4
- Coins and notes: recognising money [SHOW:money_coins]
- Telling time: hour and half hour [SHOW:clock_3pm]
""",
        },
        "life_skills": {
            0: """
CURRICULUM — Life Skills Level 0:
- Days of the week and months
- Reading simple signs: STOP, EXIT, DANGER
- Filling your name on a form
- Counting money for daily purchases
""",
        },
    }

    subject_data = curricula.get(subject, curricula["literacy"])
    level_data   = subject_data.get(level, subject_data.get(0, ""))

    return f"WHAT TO TEACH TODAY:\n{level_data}"
