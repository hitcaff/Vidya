# =============================================================================
# agent.py — Vidya Phase 5
# Added: Session tracking — Vidya remembers what was taught each session
# Run:  py -3.11 agent.py
# Open: http://localhost:7860/client
# =============================================================================

import os
import re
import uuid
from loguru import logger
from dotenv import load_dotenv

from pipecat.frames.frames import LLMRunFrame, TextFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport

from providers import get_stt, get_tts, get_transport_params
from db import init_db, get_user, save_user, update_session_count
from onboarding import build_profile_from_onboarding
from prompt_builder import build_prompt, get_onboarding_prompt
from visual_extractor import extract_visuals, visual_channel
from session_tracker import SessionTracker

load_dotenv(override=True)


def make_llm(system_prompt: str):
    from pipecat.services.google.llm import GoogleLLMService
    return GoogleLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        model="gemini-2.5-flash",
        system_instruction=system_prompt,
    )


# =============================================================================
# Visual Signal Processor — strips [SHOW:x] tags, fires visuals, tracks them
# =============================================================================

class VisualSignalProcessor(FrameProcessor):
    def __init__(self, session_id: str, tracker: SessionTracker):
        super().__init__()
        self.session_id = session_id
        self.tracker = tracker

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)

        if isinstance(frame, TextFrame) and direction == FrameDirection.DOWNSTREAM:
            clean_text, asset_keys = extract_visuals(frame.text)

            for asset_key in asset_keys:
                await visual_channel.send_show(self.session_id, asset_key)
                self.tracker.record_visual(asset_key)   # ← Track it!

            if clean_text != frame.text:
                frame = TextFrame(clean_text)

        await self.push_frame(frame, direction)


class StudentSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.user = None
        self.is_onboarding = False
        self.onboarding_answers = {}
        self.last_user_text = ""
        self.last_vidya_text = ""


async def bot(runner_args: RunnerArguments):

    await init_db()

    transport = await create_transport(
        runner_args,
        {"webrtc": lambda: get_transport_params()},
    )

    stt = get_stt()
    tts = get_tts()
    llm = make_llm(get_onboarding_prompt())

    current_session = StudentSession(str(uuid.uuid4()))
    tracker = SessionTracker(current_session.session_id)
    visual_processor = VisualSignalProcessor(current_session.session_id, tracker)

    logger.info(f"Vidya Phase 5 ready | session: {current_session.session_id}")

    messages = [{"role": "system", "content": get_onboarding_prompt()}]
    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        visual_processor,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    task = PipelineTask(pipeline)

    async def start_onboarding():
        current_session.is_onboarding = True
        messages.clear()
        messages.append({"role": "user", "content": "Begin. Ask question 1."})
        await task.queue_frames([LLMRunFrame()])
        logger.info("Onboarding started")

    async def start_teaching(user: dict, last_summary: str = None):
        """Switches Vidya from onboarding to teaching mode."""
        teaching_prompt = build_prompt(user, last_session_summary=last_summary)
        # Rebuild LLM with teaching prompt baked in
        nonlocal llm
        llm = make_llm(teaching_prompt)
        messages.clear()
        if last_summary:
            messages.append({
                "role": "user",
                "content": (
                    f"Welcome back {user['name']}! "
                    f"You remember what was taught last session. "
                    f"Start by briefly reviewing it, then begin today's lesson."
                )
            })
            logger.info(f"Returning student: {user['name']} | loading last session")
        else:
            messages.append({
                "role": "user",
                "content": (
                    f"Onboarding complete. "
                    f"Welcome {user['name']} warmly and begin their very first lesson."
                )
            })
            logger.info(f"First lesson: {user['name']}")
        await task.queue_frames([LLMRunFrame()])

    async def start_returning_session(user: dict):
        current_session.user = user
        await update_session_count(current_session.session_id)
        last_summary = await tracker.load_last_summary()
        await start_teaching(user, last_summary)

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

        # Save session summary to DB
        if current_session.user and not current_session.is_onboarding:
            summary = await tracker.save()
            logger.info(f"Session summary saved: {summary[:80]}...")

        await visual_channel.send_hide(current_session.session_id)
        await task.cancel()

    # Track conversation exchanges for the session summary
    original_assistant_push = context_aggregator.assistant().push_frame

    async def tracked_assistant_push(frame, direction=None):
        if isinstance(frame, TextFrame):
            current_session.last_vidya_text = frame.text
            # Record the exchange in the tracker
            if current_session.last_user_text:
                tracker.record_exchange(
                    current_session.last_user_text,
                    current_session.last_vidya_text
                )
        if direction:
            await original_assistant_push(frame, direction)
        else:
            await original_assistant_push(frame)

    context_aggregator.assistant().push_frame = tracked_assistant_push

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
