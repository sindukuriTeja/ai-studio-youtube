"""Pinecone vector store operations for the TV-loglines RAG dataset: create index,
upsert embeddings, and query for similar loglines.

Ported from the standalone tv_loglines_rag_system project. All configuration now
comes from backend.config.settings instead of hardcoded/local values.
"""
import time

from pinecone import Pinecone

from backend.config import settings

_client: Pinecone | None = None


def get_pinecone_client() -> Pinecone:
    global _client
    if _client is None:
        _client = Pinecone(api_key=settings.PINECONE_API_KEY)
    return _client


def create_index(pc: Pinecone) -> None:
    """Create the Pinecone index with integrated embedding if it doesn't exist yet."""
    existing = [idx.name for idx in pc.list_indexes()]
    if settings.PINECONE_INDEX_NAME in existing:
        print(f"Index '{settings.PINECONE_INDEX_NAME}' already exists.")
        return

    print(f"Creating index '{settings.PINECONE_INDEX_NAME}' with integrated inference...")
    pc.create_index_for_model(
        name=settings.PINECONE_INDEX_NAME,
        cloud="aws",
        region="us-east-1",
        embed={
            "model": settings.LOGLINE_EMBEDDING_MODEL,
            "field_map": {"text": "logline"},
        },
    )

    while not pc.describe_index(settings.PINECONE_INDEX_NAME).status.get("ready", False):
        print("  Waiting for index to be ready...")
        time.sleep(2)

    print(f"Index '{settings.PINECONE_INDEX_NAME}' is ready.")


def upsert_loglines(pc: Pinecone, loglines: list[dict]) -> None:
    """Upsert loglines into Pinecone in batches. Pinecone handles embedding server-side."""
    index = pc.Index(settings.PINECONE_INDEX_NAME)

    stats = index.describe_index_stats()
    current_count = stats.get("total_vector_count", 0)
    if current_count >= len(loglines) * 0.95:
        print(f"Index already has {current_count} vectors. Skipping upsert.")
        return

    print(f"Upserting {len(loglines)} loglines in batches of {settings.LOGLINE_BATCH_SIZE}...")
    total_upserted = 0

    for i in range(0, len(loglines), settings.LOGLINE_BATCH_SIZE):
        batch = loglines[i : i + settings.LOGLINE_BATCH_SIZE]
        records = []
        for item in batch:
            records.append({
                "_id": item["id"],
                "logline": item["logline"],
                "genre": item["genre"],
            })

        index.upsert_records(namespace="default", records=records)
        total_upserted += len(records)

        if total_upserted % (settings.LOGLINE_BATCH_SIZE * 10) == 0 or total_upserted == len(loglines):
            print(f"  Progress: {total_upserted}/{len(loglines)}")

    print(f"Upsert complete. Total records: {total_upserted}")
    time.sleep(5)


def query_similar(pc: Pinecone, query_text: str, genre: str | None = None, top_k: int | None = None) -> list[dict]:
    """Search for loglines similar to the query text."""
    index = pc.Index(settings.PINECONE_INDEX_NAME)

    filter_params = None
    if genre:
        filter_params = {"genre": {"$eq": genre}}

    results = index.search(
        namespace="default",
        top_k=top_k or settings.LOGLINE_TOP_K,
        inputs={"text": query_text},
        filter=filter_params,
        fields=["logline", "genre"],
    )

    similar_loglines = []
    for hit in results.result.hits:
        similar_loglines.append({
            "id": hit.id,
            "score": hit.score,
            "logline": hit.fields.get("logline", ""),
            "genre": hit.fields.get("genre", "unknown"),
        })

    return similar_loglines


if __name__ == "__main__":
    pc = get_pinecone_client()
    create_index(pc)
    print("\nIndex info:")
    print(pc.describe_index(settings.PINECONE_INDEX_NAME))
