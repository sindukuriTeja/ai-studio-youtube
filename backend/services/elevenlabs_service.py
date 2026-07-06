"""Generates narration audio per scene using the ElevenLabs text-to-speech API."""
from pathlib import Path

from elevenlabs.client import ElevenLabs

from backend.config import settings

_client: ElevenLabs | None = None


def _get_client() -> ElevenLabs:
    global _client
    if _client is None:
        _client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
    return _client


def generate_narration_audio(text: str, out_path: Path, voice_id: str | None = None) -> Path:
    client = _get_client()

    audio_iterator = client.text_to_speech.convert(
        voice_id=voice_id or settings.ELEVENLABS_VOICE_ID,
        text=text,
        model_id=settings.ELEVENLABS_MODEL,
        output_format="mp3_44100_128",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        for chunk in audio_iterator:
            if chunk:
                f.write(chunk)

    return out_path
