# =============================================================================
# agent.py
# Main Pipecat pipeline for Vidya — AI Literacy Teaching Bot.
#
# Phase 1: Basic voice bot with Sarvam STT + GPT-4o + Sarvam TTS.
# The pipeline is wired using providers.py — this file never imports
# from OpenAI, Sarvam, or Daily directly.
#
# Run:   python agent.py
# Test:  open the Daily room URL printed in the terminal
# =============================================================================

import os
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

load_dotenv(override=True)

# =============================================================================
# VIDYA SYSTEM PROMPT — Phase 1
# This is a basic version. It will be replaced in Phase 3 with a fully
# dynamic prompt built from the user's profile and curriculum level.
# =============================================================================

VIDYA_SYSTEM_PROMPT = """
You are Vidya, a warm and patient AI teacher. Your only purpose is to help
uneducated adults and children learn — starting with basic literacy and numeracy.

CORE RULES — never break these:
- Speak in simple, everyday words. No jargon. No complex sentences.
- Keep every response to 2-3 sentences maximum.
- Always end with a simple question or small task for the student.
- Never make the student feel bad for a wrong answer. Always say something kind first.
- Celebrate every correct answer with genuine enthusiasm.
- Speak as if you are talking to someone who has never been to school.
- Always respond in simple English only, regardless of what language the student speaks.
- Be warm, encouraging, and endlessly patient.

RIGHT NOW in Phase 1, you are just getting to know the student.
Greet them warmly, ask their name, and ask what they would like to learn.
"""


async def bot(runner_args: RunnerArguments):
    """
    Main bot entry point. Pipecat calls this when the agent starts.
    Builds the pipeline and waits for a user to connect.
    """

    # ------------------------------------------------------------------
    # Step 1: Create transport — free WebRTC, no account needed
    # ------------------------------------------------------------------
    transport = await create_transport(
        runner_args,
        {
            "webrtc": lambda: get_transport_params(),
        },
    )

    # ------------------------------------------------------------------
    # Step 2: Initialise AI services — all via providers.py
    # ------------------------------------------------------------------
    stt = get_stt()    # Sarvam Saarika v2.5 — auto language detect
    tts = get_tts()    # Sarvam Bulbul v3 — pace=0.8, slow clear speech
    llm = get_llm()    # OpenAI GPT-4o — the teaching brain

    logger.info("AI services initialised via providers.py")
    logger.info(f"  STT: {stt.__class__.__name__}")
    logger.info(f"  LLM: {llm.__class__.__name__}")
    logger.info(f"  TTS: {tts.__class__.__name__}")

    # ------------------------------------------------------------------
    # Step 3: Set up conversation context with Vidya's system prompt
    # ------------------------------------------------------------------
    messages = [
        {
            "role": "system",
            "content": VIDYA_SYSTEM_PROMPT,
        }
    ]
    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)

    # ------------------------------------------------------------------
    # Step 4: Build the Pipecat pipeline
    #
    # Audio flows in this exact sequence:
    #   Browser Mic
    #     → Daily WebRTC transport.input()
    #     → Sarvam STT (speech → text)
    #     → context_aggregator.user() (adds user turn to history)
    #     → GPT-4o LLM (generates teaching response)
    #     → Sarvam TTS (text → speech)
    #     → Daily WebRTC transport.output()
    #     → Browser Speaker
    #     → context_aggregator.assistant() (saves assistant turn to history)
    # ------------------------------------------------------------------
    pipeline = Pipeline([
        transport.input(),              # Receive audio from browser
        stt,                            # Convert speech to text
        context_aggregator.user(),      # Add user message to context
        llm,                            # Generate response
        tts,                            # Convert response to speech
        transport.output(),             # Send audio to browser
        context_aggregator.assistant(), # Save assistant response to context
    ])

    task = PipelineTask(pipeline)

    # ------------------------------------------------------------------
    # Step 5: Event handlers
    # ------------------------------------------------------------------

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        """
        Called when a user opens the browser and connects.
        Vidya introduces herself and starts the conversation.
        """
        logger.info(f"Student connected: {client}")

        # Trigger Vidya to speak her opening greeting
        messages.append({
            "role": "system",
            "content": (
                "A student has just connected. "
                "Greet them warmly in a friendly voice. "
                "Introduce yourself as Vidya. "
                "Ask their name and what language they speak. "
                "Keep it to 2-3 sentences."
            )
        })
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        """
        Called when the user closes the browser tab or disconnects.
        """
        logger.info(f"Student disconnected: {client}")
        # Phase 2 will save session progress to DB here
        await task.cancel()

    # ------------------------------------------------------------------
    # Step 6: Run the pipeline — waits for connections
    # ------------------------------------------------------------------
    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
