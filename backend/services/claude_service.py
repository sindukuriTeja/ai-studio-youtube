"""Uses Claude to turn a film idea into a script + shot-by-shot breakdown."""
import json
import re

from anthropic import Anthropic

from backend.config import settings
from backend.models import Scene, Script

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


SYSTEM_PROMPT = """You are a professional short-film screenwriter and AI video-generation prompt \
engineer working for an "AI Film Studio" pipeline. Given a film idea, you write a tight script \
broken into scenes, plus a Runway-ready text-to-video prompt for each scene.

Rules:
- Respond with ONLY valid JSON, no markdown fences, no commentary.
- JSON shape:
{
  "title": "string",
  "logline": "one sentence summary",
  "scenes": [
    {
      "title": "short scene title",
      "narration": "1-3 sentences of narration/voiceover for this scene",
      "video_prompt": "a vivid, concrete, camera-aware visual description for an AI video generator. \
Describe setting, subject, action, lighting, camera movement. Keep it under 400 characters. \
Do not include dialogue or text overlays."
    }
  ]
}
- Each scene's video_prompt must describe a single continuous shot achievable in 5-10 seconds of video.
- Keep narration concise; it will be read aloud and should roughly match the pacing of a short clip.
- Maintain visual/character/setting consistency across scenes where relevant.
- CRITICAL for video_prompt only: Runway AI has strict content moderation. \
Write video prompts using only safe, visual, cinematic language. \
Never use words like: war, kill, murder, attack, blood, weapon, gun, shoot, fight, explosion, \
crime, syndicate, dead, death, corpse, violence, assassin, terrorist, bomb, gang, drug, hostage. \
Instead describe the same scene using neutral cinematic terms: \
tense confrontation → "two figures face each other in a dark alley, dramatic low-key lighting"; \
battle scene → "soldiers moving through dense jungle, fog, aerial shot, golden hour"; \
someone being taken → "a figure is led away through a dimly lit corridor, silhouettes". \
The narration can tell the real story — the video_prompt just needs to pass content moderation.
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(json)?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def generate_script(idea: str, num_scenes: int, style: str | None = None) -> Script:
    client = _get_client()

    style_line = f"\nVisual style to apply consistently: {style}\n" if style else ""
    user_prompt = (
        f"Film idea: {idea}\n"
        f"Number of scenes: {num_scenes}{style_line}\n"
        "Write the script and scene breakdown as specified."
    )

    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text_parts = [block.text for block in response.content if block.type == "text"]
    raw_text = "\n".join(text_parts)
    data = _extract_json(raw_text)

    scenes = [
        Scene(
            index=i,
            title=s.get("title", f"Scene {i + 1}"),
            narration=s.get("narration", ""),
            video_prompt=s.get("video_prompt", ""),
        )
        for i, s in enumerate(data.get("scenes", []))
    ]

    return Script(
        title=data.get("title", "Untitled Film"),
        logline=data.get("logline", idea),
        scenes=scenes,
    )
