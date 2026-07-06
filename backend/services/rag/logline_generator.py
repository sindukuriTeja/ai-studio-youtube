"""Claude-powered logline generation using RAG context (similar existing TV episode
loglines retrieved from Pinecone). Returns a clean list of strings so it can be
consumed programmatically by the film pipeline and rendered directly in the UI.
"""
import json
import re

from anthropic import Anthropic

from backend.config import settings

SYSTEM_PROMPT = """You are an expert TV writer's room assistant. Your job is to generate \
original, compelling TV episode loglines. Each logline should be 1-3 sentences, introduce \
a clear conflict or hook, and hint at stakes. Never copy existing loglines — create fresh, \
original ideas inspired by the patterns and themes you see in the examples.

Respond with ONLY valid JSON, no markdown fences, no commentary.
JSON shape:
{
  "loglines": ["logline 1", "logline 2", ...]
}
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
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


def generate_loglines(
    client: Anthropic,
    user_idea: str,
    similar_loglines: list[dict],
    num_loglines: int = 3,
    genre: str | None = None,
) -> list[str]:
    """Generate new TV episode loglines inspired by the user's idea and similar examples."""

    examples_text = "\n".join(
        f"  {i + 1}. [{item['genre'].upper()}] {item['logline']}"
        for i, item in enumerate(similar_loglines)
    ) or "  (no close matches found — rely on general TV storytelling craft)"

    genre_instruction = f"The loglines should be in the **{genre}** genre." if genre else ""

    user_prompt = f"""Based on the following story idea, generate {num_loglines} original TV episode loglines.

**Story Idea:** {user_idea}

{genre_instruction}

Here are similar existing loglines for inspiration (DO NOT copy these — use them only to \
understand tone, structure, and style):

{examples_text}

---

Now generate {num_loglines} completely original loglines that explore the user's story idea \
from different angles. Each should be unique in premise and conflict."""

    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": user_prompt}],
        system=SYSTEM_PROMPT,
    )

    text_parts = [block.text for block in response.content if block.type == "text"]
    raw_text = "\n".join(text_parts)
    data = _extract_json(raw_text)
    loglines = [l.strip() for l in data.get("loglines", []) if l and l.strip()]
    return loglines
