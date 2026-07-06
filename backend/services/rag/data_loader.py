"""Load and clean TV loglines from JSONL files, for one-time ingestion into Pinecone.

Ported from the standalone tv_loglines_rag_system project. Only needed by
scripts/ingest_loglines.py — the live app just queries an already-populated index.
"""
import json
import os
import re
from typing import Generator

from backend.config import settings

GENRE_FILES = {
    "comedy": "comedy_loglines.jsonl",
    "drama": "drama_loglines.jsonl",
    "horror": "horror_loglines.jsonl",
    "scifi": "scifi_loglines.jsonl",
}


def clean_logline(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\x20-\x7E''""—–…]", "", text)
    if not text.endswith((".", "!", "?")):
        text += "."
    return text


def load_genre_loglines() -> Generator[dict, None, None]:
    """Yield loglines with genre metadata from genre-specific files."""
    data_dir = str(settings.LOGLINE_DATA_DIR)
    for genre, filename in GENRE_FILES.items():
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found, skipping.")
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    logline = record.get("logline", "").strip()
                    if logline and len(logline) > 20:
                        yield {
                            "id": f"{genre}_{line_num}",
                            "logline": clean_logline(logline),
                            "genre": genre,
                        }
                except json.JSONDecodeError:
                    continue


def load_all_loglines() -> list[dict]:
    """Load all loglines into memory."""
    loglines = list(load_genre_loglines())
    print(f"Loaded {len(loglines)} loglines across {len(GENRE_FILES)} genres.")
    return loglines


if __name__ == "__main__":
    data = load_all_loglines()
    for genre in GENRE_FILES:
        count = sum(1 for d in data if d["genre"] == genre)
        print(f"  {genre}: {count}")
    if data:
        print(f"\nSample: {data[0]}")
