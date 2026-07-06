"""Generates video clips per scene using the RunwayML API (Gen-4.5 text-to-video)."""
import re
from pathlib import Path

import httpx
from runwayml import RunwayML, TaskFailedError

from backend.config import settings

_client: RunwayML | None = None

# Words that reliably trigger Runway's SAFETY.INPUT.TEXT filter
_BLOCKED_TERMS = re.compile(
    r"\b(war|kill(?:ed|ing|s)?|murder(?:ed|ing|s)?|attack(?:ed|ing|s)?|blood(?:y)?|"
    r"weapon(?:s)?|gun(?:s|fire|shot)?|shoot(?:ing|s)?|shot|fight(?:ing|s)?|"
    r"explo(?:sion|de|ding|des)|crime|syndicate|dead|death|corpse(?:s)?|"
    r"violen(?:t|ce)|assassin(?:ate|ation|s)?|terror(?:ist|ism|s)?|"
    r"bomb(?:s|ing|ed)?|gang(?:s|ster)?|drug(?:s)?|hostage(?:s)?|"
    r"stab(?:bed|bing)?|slash(?:ed|ing)?|wound(?:ed|ing|s)?|threaten(?:ing|s)?|"
    r"ambush(?:ed|ing)?|execut(?:e|ion|ing|ed)?|destroy(?:ed|ing|s)?)\b",
    re.IGNORECASE,
)

_SAFE_FALLBACK = (
    "A lone figure stands at the edge of a city at dusk, silhouetted against a vibrant orange sky. "
    "Slow cinematic pan, moody atmospheric lighting."
)


def _sanitize_prompt(text: str) -> str:
    """Remove flagged terms and return a cleaned prompt, or a safe fallback if too much is stripped."""
    cleaned = _BLOCKED_TERMS.sub("", text).strip()
    # If we stripped too much (less than half the original), use the fallback
    if len(cleaned) < len(text) * 0.5:
        return _SAFE_FALLBACK
    return cleaned


def _get_client() -> RunwayML:
    global _client
    if _client is None:
        _client = RunwayML(api_key=settings.RUNWAYML_API_SECRET)
    return _client


class RunwayGenerationError(Exception):
    pass


def generate_scene_video(
    prompt_text: str,
    out_path: Path,
    ratio: str = "1280:720",
    duration: int = 5,
    prompt_image: str | None = None,
) -> Path:
    """Submits a generation task to Runway, waits for completion, downloads the result.

    If prompt_image is None, uses pure text-to-video mode (Gen-4.5 supports this by
    omitting the promptImage parameter).
    """
    client = _get_client()

    # Try with the original prompt first, then fall back to sanitized on moderation failure
    prompts_to_try = [prompt_text, _sanitize_prompt(prompt_text), _SAFE_FALLBACK]
    # Deduplicate while preserving order
    seen: set[str] = set()
    prompts_to_try = [p for p in prompts_to_try if not (p in seen or seen.add(p))]

    last_error: Exception | None = None
    for attempt_prompt in prompts_to_try:
        try:
            if prompt_image:
                task = client.image_to_video.create(
                    model=settings.RUNWAY_MODEL,
                    prompt_text=attempt_prompt,
                    prompt_image=prompt_image,
                    ratio=ratio,
                    duration=duration,
                ).wait_for_task_output()
            else:
                task = client.text_to_video.create(
                    model=settings.RUNWAY_MODEL,
                    prompt_text=attempt_prompt,
                    ratio=ratio,
                    duration=duration,
                ).wait_for_task_output()
            break  # success — exit retry loop
        except TaskFailedError as e:
            details = str(e.task_details) if hasattr(e, "task_details") else str(e)
            if "SAFETY" in details or "moderation" in details.lower():
                last_error = RunwayGenerationError(f"Runway moderation blocked prompt: {details}")
                continue  # retry with sanitized prompt
            raise RunwayGenerationError(f"Runway task failed: {details}") from e
    else:
        raise last_error or RunwayGenerationError("All prompt attempts blocked by Runway moderation")

    if not task.output:
        raise RunwayGenerationError("Runway task completed but returned no output")

    video_url = task.output[0]
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with httpx.stream("GET", video_url, timeout=120.0) as response:
        response.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)

    return out_path
