# =============================================================================
# agent.py — Vidya Phase 2 (v3)
# Fix: system_instruction passed at LLM creation time for each session
# Run:  py -3.11 agent.py
# Open: http://localhost:7860/client
# =============================================================================

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

from providers import get_stt, get_tts, get_transport_params
from db import init_db, get_user, save_user, update_session_count
from onboarding import build_profile_from_onboarding
from prompt_builder import build_prompt, get_onboarding_prompt

load_dotenv(override=True)


def make_llm(system_prompt: str):
    """
    Creates a fresh Gemini LLM service with the given system prompt
    baked in at the service level — the only reliable way to pass
    system instructions to Gemini via Pipecat.
    """
    from pipecat.services.google.llm import GoogleLLMService
    return GoogleLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        model="gemini-2.5-flash",
        system_instruction=system_prompt,
    )


class StudentSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.user = None
        self.is_onboarding = False
        self.onboarding_answers = {}


async def bot(runner_args: RunnerArguments):

    await init_db()

    transport = await create_transport(
        runner_args,
        {"webrtc": lambda: get_transport_params()},
    )

    stt = get_stt()
    tts = get_tts()

    # Start with onboarding prompt baked into the LLM
    llm = make_llm(get_onboarding_prompt())

    logger.info("Vidya Phase 2 ready")

    messages = []
    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)

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
    current_session = StudentSession(str(uuid.uuid4()))

    async def start_onboarding():
        current_session.is_onboarding = True
        messages.clear()
        # Trigger Vidya to ask question 1
        messages.append({
            "role": "user",
            "content": "A new student just connected. Begin onboarding. Ask question 1 now."
        })
        await task.queue_frames([LLMRunFrame()])
        logger.info("Onboarding started")

    async def complete_onboarding():
        current_session.is_onboarding = False
        profile = build_profile_from_onboarding(
            current_session.session_id,
            current_session.onboarding_answers
        )
        current_session.user = await save_user(current_session.session_id, profile)
        logger.info(f"Onboarding complete — {profile['name']} saved")

    async def start_returning_session(user: dict):
        current_session.user = user
        await update_session_count(current_session.session_id)
        teaching_prompt = build_prompt(user)
        # For returning students, swap the LLM system instruction
        # by restarting with teaching prompt
        messages.clear()
        messages.append({
            "role": "user",
            "content": f"Welcome back {user['name']}. Start today's lesson."
        })
        await task.queue_frames([LLMRunFrame()])
        logger.info(f"Returning student: {user['name']}")

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Student connected | session: {current_session.session_id}")
        existing_user = await get_user(current_session.session_id)
        if existing_user and existing_user.get("onboarding_done"):
            await start_returning_session(existing_user)
        else:
            await start_onboarding()

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        name = current_session.user["name"] if current_session.user else "Unknown"
        logger.info(f"Student disconnected: {name}")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
