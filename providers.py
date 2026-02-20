# =============================================================================
# providers.py
# THE ONLY FILE THAT KNOWS WHICH EXTERNAL SERVICES ARE BEING USED.
#
# Updated: Removed Daily.co transport — now uses Pipecat's built-in
# WebRTC transport which is completely free, no account needed.
#
# To swap any service in the future — change ONLY the relevant function here.
# =============================================================================

import os
from dotenv import load_dotenv

from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.transports.base_transport import TransportParams

load_dotenv(override=True)


def get_llm():
    from pipecat.services.groq.llm import GroqLLMService
    return GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
    )


def get_stt():
    """
    Returns the Speech-to-Text service.
    To swap to Whisper, Deepgram, Google STT — change ONLY this function.

    language="unknown" = auto-detects Hindi, Telugu, Tamil, Kannada, etc.
    Never force users to select a language.
    """
    return SarvamSTTService(
        api_key=os.getenv("SARVAM_API_KEY"),
        language="unknown",
        model="saarika:v2.5",
    )


def get_tts():
    """
    Returns the Text-to-Speech service.
    To swap to ElevenLabs, Azure TTS — change ONLY this function.

    pace=0.8 = slightly slower speech — important for uneducated learners.
    """
    return SarvamTTSService(
        api_key=os.getenv("SARVAM_API_KEY"),
        target_language_code="en-IN",
        model="bulbul:v3",
        speaker="priya",
        pace=0.8,
        speech_sample_rate=24000,
    )


def get_transport_params():
    """
    Returns WebRTC transport parameters.
    Free, no account needed, works directly in the browser.

    To swap to Daily.co or LiveKit in the future — change ONLY this function.

    Example swap back to Daily.co:
        from pipecat.transports.daily.transport import DailyParams
        return DailyParams(audio_in_enabled=True, audio_out_enabled=True)
    """
    return TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
    )
