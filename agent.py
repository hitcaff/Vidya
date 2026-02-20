# =============================================================================
# agent.py
# Main Pipecat pipeline for Vidya — AI Literacy Teaching Bot.
#
# Phase 2: Added onboarding flow + user profiles + session memory.
#
# New behaviour:
#   - New user  → runs 7-question onboarding → saves profile to DB
#   - Returning user → loads profile from DB → resumes where they left off
#
# Run:  py -3.11 agent.py
# Open: http://localhost:7860/client
# =============================================================================
from pipecat.frames.frames import TTSSpeakFrame
import os
import uuid
from loguru import logger
from dotenv import load_dotenv

from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport

from providers import get_llm, get_stt, get_tts, get_transport_params
from db import init_db, get_user, save_user, update_session_count
from onboarding import build_profile_from_onboarding
from prompt_builder import build_prompt, get_onboarding_prompt

load_dotenv(override=True)


# =============================================================================
# Session state — tracks each connected student in memory
# =============================================================================

class StudentSession:
    """
    Holds the in-memory state for one connected student.
    Created when they connect, discarded when they disconnect.
    """
    def __init__(self, session_id: str):
        self.session_id     = session_id
        self.user           = None          # Loaded from DB (None if new)
        self.is_onboarding  = False         # True while running onboarding
        self.onboarding_answers = {}        # Collects answers during onboarding
        self.messages       = []            # Full conversation history


# =============================================================================
# Main bot entry point
# =============================================================================

async def bot(runner_args: RunnerArguments):
    """
    Main Pipecat entry point.
    Builds the pipeline and manages student sessions.
    """

    # Initialise the database on startup
    await init_db()

    # ------------------------------------------------------------------
    # Transport + AI services — all via providers.py
    # ------------------------------------------------------------------
    transport = await create_transport(
        runner_args,
        {"webrtc": lambda: get_transport_params()},
    )

    stt = get_stt()
    tts = get_tts()
    llm = get_llm()

    logger.info("Vidya Phase 2 ready")
    logger.info(f"  STT: {stt.__class__.__name__}")
    logger.info(f"  LLM: {llm.__class__.__name__}")
    logger.info(f"  TTS: {tts.__class__.__name__}")

    # ------------------------------------------------------------------
    # Conversation context — starts empty, filled per student
    # ------------------------------------------------------------------
    messages = []
    context  = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------
    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    task = PipelineTask(pipeline)

    # Active session state
    current_session = StudentSession(str(uuid.uuid4()))

    # ------------------------------------------------------------------
    # Helper: set the system prompt
    # ------------------------------------------------------------------
    def set_system_prompt(prompt: str):
        """Replaces the system message in the conversation."""
        messages.clear()
        messages.append({"role": "system", "content": prompt})

    # ------------------------------------------------------------------
    # Helper: check if onboarding is complete
    # ------------------------------------------------------------------
    def check_onboarding_complete(text: str) -> bool:
        """Returns True if the LLM signalled onboarding is done."""
        return "[ONBOARDING_COMPLETE]" in text

    # ------------------------------------------------------------------
    # Helper: start onboarding for a new student
    # ------------------------------------------------------------------
    async def start_onboarding():
    	current_session.is_onboarding = True
    	messages.clear()
    	messages.append({
        	"role": "system",
        	"content": get_onboarding_prompt()
    })
    # Force Vidya to say the exact greeting via TTS directly
    # bypassing the LLM entirely for the opening line
    await task.queue_frames([
        TTSSpeakFrame("Hello! I am Vidya, your teacher. I am so happy to meet you! What is your name?")
    ])
    logger.info(f"Onboarding started for session {current_session.session_id}")
    messages.append({
        "role": "assistant", 
        "content": "Hello! I am Vidya, your teacher. I am so happy to meet you! What is your name?"
    })
    messages.append({
        "role": "system",
        "content": get_onboarding_prompt()
    })
    await task.queue_frames([LLMRunFrame()])
    logger.info(f"Onboarding started for session {current_session.session_id}")

    # ------------------------------------------------------------------
    # Helper: finish onboarding, save profile, start teaching
    # ------------------------------------------------------------------
    async def complete_onboarding(llm_response: str):
        current_session.is_onboarding = False

        # Build and save the user profile
        profile = build_profile_from_onboarding(
            current_session.session_id,
            current_session.onboarding_answers
        )
        current_session.user = await save_user(current_session.session_id, profile)

        logger.info(f"Onboarding complete — {profile['name']} saved to DB")

        # Switch to the teaching prompt
        teaching_prompt = build_prompt(current_session.user)
        set_system_prompt(teaching_prompt)

        # Vidya transitions smoothly into the first lesson
        messages.append({
            "role": "system",
            "content": (
                f"Onboarding is complete. {profile['name']} is ready to learn. "
                f"Warmly welcome them and begin their very first lesson. "
                f"Keep it gentle and exciting."
            )
        })
        await task.queue_frames([LLMRunFrame()])

    # ------------------------------------------------------------------
    # Helper: start a session for a returning student
    # ------------------------------------------------------------------
    async def start_returning_session(user: dict):
        current_session.user = user
        await update_session_count(current_session.session_id)

        teaching_prompt = build_prompt(user)
        set_system_prompt(teaching_prompt)

        messages.append({
    "role": "system",
    "content": (
        "You are Vidya, a teacher. A student just connected. "
        "Your ONLY job is to teach. "
        "Say EXACTLY this and nothing else: "
        "Hello! I am Vidya, your teacher. I am so happy to meet you! What is your name?"
    )
})
        await task.queue_frames([LLMRunFrame()])
        logger.info(f"Returning student: {user['name']} | session #{user['session_count']}")

    # ------------------------------------------------------------------
    # Event: student connects
    # ------------------------------------------------------------------
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Student connected | session: {current_session.session_id}")

        # Check if this student has been here before
        existing_user = await get_user(current_session.session_id)

        if existing_user and existing_user.get("onboarding_done"):
            # Returning student — load their profile and resume
            await start_returning_session(existing_user)
        else:
            # New student — run onboarding
            await start_onboarding()

    # ------------------------------------------------------------------
    # Event: student disconnects
    # ------------------------------------------------------------------
    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        name = current_session.user["name"] if current_session.user else "Unknown"
        logger.info(f"Student disconnected: {name}")
        # Phase 5 will save session summary to DB here
        await task.cancel()

    # ------------------------------------------------------------------
    # Monitor LLM output for onboarding completion signal
    # Note: In a future version this will use a proper frame processor.
    # For Phase 2, we check the context after each exchange.
    # ------------------------------------------------------------------
    original_push = context_aggregator.assistant().push_frame

    # ------------------------------------------------------------------
    # Run the pipeline
    # ------------------------------------------------------------------
    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
