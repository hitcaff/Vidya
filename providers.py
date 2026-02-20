# =============================================================================
# providers.py
# THE ONLY FILE THAT KNOWS WHICH EXTERNAL SERVICES ARE BEING USED.
#
# To swap the LLM, STT, TTS, or transport — change ONLY the relevant
# function here. Every other file in the project calls these functions
# and never imports from OpenAI, Sarvam, or Daily directly.
# =============================================================================

import os
from dotenv import load_dotenv

from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.transports.daily.transport import DailyParams
from pipecat.transports.base_transport import TransportParams

load_dotenv(override=True)


def get_llm():
    """
    Returns the LLM service.
    To swap to Claude, Gemini, Mistral, or any future model —
    change ONLY this function. Nothing else in the codebase changes.

    Example swap to Claude:
        from pipecat.services.anthropic.llm import AnthropicLLMService
        return AnthropicLLMService(api_key=os.getenv("ANTHROPIC_API_KEY"), model="claude-opus-4-5")
    """
    return OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",           # Always gpt-4o for Vidya — teaching needs full intelligence
    )


def get_stt():
    """
    Returns the Speech-to-Text service.
    To swap to Whisper, Deepgram, Google STT, or Azure —
    change ONLY this function.

    language="unknown" = Sarvam auto-detects the language.
    This is critical for Vidya — never force users to select a language.

    Example swap to Whisper:
        from pipecat.services.openai.stt import OpenAISTTService
        return OpenAISTTService(api_key=os.getenv("OPENAI_API_KEY"), model="whisper-1")
    """
    return SarvamSTTService(
        api_key=os.getenv("SARVAM_API_KEY"),
        language="unknown",       # Auto-detect: Hindi, Telugu, Tamil, Kannada, etc.
        model="saarika:v2.5",
    )


def get_tts():
    """
    Returns the Text-to-Speech service.
    To swap to ElevenLabs, Azure TTS, Google TTS —
    change ONLY this function.

    pace=0.8 = slightly slower than normal — critical for uneducated learners
    who need time to hear and process each word.

    speaker="priya" = warm female voice, friendly and patient-sounding.
    Other options — Female: ritu, neha, pooja, simran, kavya, ishita
                    Male:   aditya, anand, rohan, rahul, amit

    Example swap to ElevenLabs:
        from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
        return ElevenLabsTTSService(api_key=os.getenv("ELEVENLABS_API_KEY"), voice_id="...")
    """
    return SarvamTTSService(
        api_key=os.getenv("SARVAM_API_KEY"),
        target_language_code="en-IN",   # Default; overridden dynamically once user language is known
        model="bulbul:v3",
        speaker="priya",
        pace=0.8,                       # Slow, clear speech for learners
        speech_sample_rate=24000,
    )


def get_transport_params():
    """
    Returns transport parameters for Daily.co (WebRTC browser transport).
    To swap to LiveKit, Twilio, or plain WebRTC —
    change ONLY this function.

    Example swap to LiveKit:
        from pipecat.transports.livekit.transport import LiveKitParams
        return LiveKitParams(audio_in_enabled=True, audio_out_enabled=True)
    """
    return DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
    )


def get_webrtc_transport_params():
    """
    Fallback plain WebRTC transport params (used when Daily.co is not available).
    """
    return TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
    )
