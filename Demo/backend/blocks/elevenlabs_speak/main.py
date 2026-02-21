"""ElevenLabs TTS block — converts text to speech via ElevenLabs API."""

import os
import uuid
from pathlib import Path

import httpx


async def execute(inputs: dict, context: dict) -> dict:
    text = inputs["text"][:5000]
    voice_id = inputs.get("voice_id", "21m00Tcm4TlvDq8ikWAM")  # Rachel default

    api_key = os.environ.get("ELEVENLABS_API_KEY", "")

    if not api_key or api_key == "...":
        print(f"[TTS STUB] text={text[:80]}...")
        return {"audio_url": "", "duration_seconds": len(text) * 0.06}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_monolingual_v1"},
        )

    if resp.status_code == 200:
        audio_dir = Path("static/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)
        filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
        audio_path = audio_dir / filename
        audio_path.write_bytes(resp.content)
        return {
            "audio_url": f"/static/audio/{filename}",
            "duration_seconds": round(len(resp.content) / 16000, 1),
        }

    return {"audio_url": "", "duration_seconds": 0}
