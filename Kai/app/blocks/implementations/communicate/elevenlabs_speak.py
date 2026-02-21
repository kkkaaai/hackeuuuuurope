from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from app.blocks.executor import register_implementation
from app.config import settings

logger = logging.getLogger("agentflow.blocks.elevenlabs")

AUDIO_DIR = Path(__file__).parent.parent.parent.parent / "audio_output"


@register_implementation("elevenlabs_speak")
async def elevenlabs_speak(inputs: dict[str, Any]) -> dict[str, Any]:
    """Convert text to speech using ElevenLabs TTS."""
    text = inputs["text"]
    voice_id = inputs.get("voice_id", "21m00Tcm4TlvDq8ikWAM")  # Rachel default

    if not settings.elevenlabs_api_key:
        raise ValueError("ELEVENLABS_API_KEY not configured — add it to .env")

    try:
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=settings.elevenlabs_api_key)

        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
        output_path = AUDIO_DIR / filename

        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
        )

        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
    except Exception as e:
        logger.error("ElevenLabs API error: %s", e)
        raise ValueError(f"ElevenLabs TTS failed: {type(e).__name__}") from None

    return {
        "audio_url": f"/audio/{filename}",
        "duration_seconds": len(text) * 0.06,
    }
