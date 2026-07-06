"""Pydantic schemas shared across the backend."""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class FilmRequest(BaseModel):
    idea: str = Field(..., min_length=3, description="The film idea / premise / logline")
    num_scenes: int = Field(4, ge=1, le=10, description="How many scenes/shots to generate")
    style: Optional[str] = Field(None, description="Visual style, e.g. 'cinematic noir', 'anime'")
    genre: Optional[Literal["comedy", "drama", "horror", "scifi"]] = Field(
        None,
        description=(
            "Optional TV genre used for the RAG inspiration step: retrieves similar "
            "existing TV episode loglines from that genre and has Claude refine the "
            "idea into a tighter logline before scriptwriting. Ignored if the RAG "
            "system (Pinecone) isn't configured."
        ),
    )
    aspect_ratio: str = Field("1280:720", description="Runway video aspect ratio")
    scene_duration: int = Field(5, description="Seconds per generated video clip (5 or 10)")
    voice_id: Optional[str] = Field(None, description="Override ElevenLabs voice id")
    include_narration: bool = Field(True, description="Whether to generate voiceover narration")


class SimilarLogline(BaseModel):
    """An existing TV episode logline retrieved from the Pinecone RAG index."""

    logline: str
    genre: str
    score: float


class Scene(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    index: int
    title: str
    narration: str
    video_prompt: str
    image_prompt: Optional[str] = None
    video_url: Optional[str] = None
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    status: Literal["pending", "generating", "done", "error"] = "pending"
    error: Optional[str] = None


class Script(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: str
    logline: str
    scenes: list[Scene]


class JobStatus(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    job_id: str
    status: Literal[
        "pending",
        "finding_inspiration",
        "writing_script",
        "generating_scenes",
        "assembling",
        "done",
        "error",
    ]
    progress: float = 0.0
    message: str = ""
    script: Optional[Script] = None
    final_video_path: Optional[str] = None
    error: Optional[str] = None

    # RAG inspiration step (best-effort; populated only if Pinecone is configured
    # and returns matches). refined_logline is what's actually handed to Claude's
    # script writer — it falls back to the user's raw idea otherwise.
    refined_logline: Optional[str] = None
    inspired_by: Optional[list[SimilarLogline]] = None
