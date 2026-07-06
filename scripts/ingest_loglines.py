"""One-time data ingestion for the TV-loglines RAG system.

Populates the Pinecone index (PINECONE_INDEX_NAME, default "tv-loglines") from
JSONL files on disk. Only needs to be run once per Pinecone project/index — the
live app (backend/services/rag_service.py) just queries an already-populated
index during film generation.

Usage:
    python scripts/ingest_loglines.py

Expects LOGLINE_DATA_DIR (see .env / .env.example) to contain:
    comedy_loglines.jsonl
    drama_loglines.jsonl
    horror_loglines.jsonl
    scifi_loglines.jsonl
"""
import sys
from pathlib import Path

# Make the "backend" package importable when run as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.rag.data_loader import load_all_loglines
from backend.services.rag.vector_store import get_pinecone_client, create_index, upsert_loglines


def main():
    print("=" * 60)
    print("TV Loglines RAG System — Data Ingestion")
    print("=" * 60)

    print("\n[1/3] Loading loglines from JSONL files...")
    loglines = load_all_loglines()
    if not loglines:
        print("\nNo loglines found. Check LOGLINE_DATA_DIR in your .env file.")
        return

    print("\n[2/3] Connecting to Pinecone and creating index...")
    pc = get_pinecone_client()
    create_index(pc)

    print("\n[3/3] Upserting loglines into Pinecone...")
    upsert_loglines(pc, loglines)

    print("\n" + "=" * 60)
    print("Ingestion complete! Your vector database is ready.")
    print("=" * 60)


if __name__ == "__main__":
    main()
