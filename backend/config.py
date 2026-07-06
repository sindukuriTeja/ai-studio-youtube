"""Central configuration loaded from environment variables (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    # Anthropic / Claude
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    # RunwayML
    RUNWAYML_API_SECRET: str = os.getenv("RUNWAYML_API_SECRET", "")
    RUNWAY_MODEL: str = os.getenv("RUNWAY_MODEL", "gen4.5")

    # ElevenLabs
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_MODEL: str = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")

    # Pinecone / TV-loglines RAG (idea -> similar loglines -> refined logline).
    # Optional: the film pipeline falls back to the user's raw idea if this isn't set.
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "tv-loglines")
    LOGLINE_EMBEDDING_MODEL: str = os.getenv("LOGLINE_EMBEDDING_MODEL", "multilingual-e5-large")
    LOGLINE_TOP_K: int = int(os.getenv("LOGLINE_TOP_K", "10"))
    LOGLINE_BATCH_SIZE: int = int(os.getenv("LOGLINE_BATCH_SIZE", "96"))

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Storage
    STORAGE_DIR: Path = BASE_DIR / os.getenv("STORAGE_DIR", "./storage").lstrip("./")
    LOGLINE_DATA_DIR: Path = BASE_DIR / os.getenv("LOGLINE_DATA_DIR", "./tv_loglines_dataset").lstrip("./")

    def validate(self) -> list[str]:
        """Return a list of human-readable problems with the REQUIRED core pipeline
        config (Claude/Runway/ElevenLabs), empty if all good. RAG/Pinecone is
        intentionally excluded — it's an optional enhancement, not a hard requirement."""
        problems = []
        if not self.ANTHROPIC_API_KEY:
            problems.append("ANTHROPIC_API_KEY is not set")
        if not self.RUNWAYML_API_SECRET:
            problems.append("RUNWAYML_API_SECRET is not set")
        if not self.ELEVENLABS_API_KEY:
            problems.append("ELEVENLABS_API_KEY is not set")
        return problems

    def rag_configured(self) -> bool:
        """Whether the TV-loglines RAG inspiration step is usable."""
        return bool(self.PINECONE_API_KEY)


settings = Settings()
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
