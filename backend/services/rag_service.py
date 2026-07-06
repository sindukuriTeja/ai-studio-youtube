"""Facade over the TV-loglines RAG system (Pinecone retrieval + Claude generation).

This is the "story idea -> similar existing TV loglines -> fresh original loglines"
system, integrated as an automatic first step of the film pipeline: the user's raw
idea is used to retrieve similar real TV episode loglines, and Claude uses those as
grounding to draft a few tighter, more original loglines. The first (best) result
becomes the premise that's actually handed to the script writer.

This step is best-effort: if PINECONE_API_KEY isn't configured, or Pinecone/Claude
fail for any reason, we fall back to the user's raw idea untouched rather than
failing the whole film job.
"""
from anthropic import Anthropic

from backend.config import settings
from backend.models import SimilarLogline
from backend.services.rag import vector_store
from backend.services.rag.logline_generator import generate_loglines

_claude_client: Anthropic | None = None


def _get_claude_client() -> Anthropic:
    global _claude_client
    if _claude_client is None:
        _claude_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _claude_client


def suggest_loglines(
    idea: str,
    genre: str | None = None,
    num_loglines: int = 3,
) -> tuple[list[str], list[SimilarLogline]]:
    """Retrieve similar existing loglines from Pinecone and generate fresh ones with Claude.

    Returns (generated_loglines, similar_loglines). Returns ([], []) if the RAG
    system isn't configured — callers should treat that as "no suggestion available"
    and fall back to the user's original idea.
    """
    if not settings.rag_configured():
        return [], []

    pc = vector_store.get_pinecone_client()
    raw_similar = vector_store.query_similar(pc, idea, genre=genre, top_k=settings.LOGLINE_TOP_K)
    similar = [
        SimilarLogline(
            logline=item["logline"],
            genre=item["genre"],
            score=item["score"],
        )
        for item in raw_similar
    ]

    if not raw_similar:
        return [], []

    client = _get_claude_client()
    loglines = generate_loglines(
        client,
        user_idea=idea,
        similar_loglines=raw_similar,
        num_loglines=num_loglines,
        genre=genre,
    )

    return loglines, similar
