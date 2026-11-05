
from functools import lru_cache
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from backend.core.config import settings


COLLECTION_NAME = "secure_rag_documents"


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Create and cache a persistent local Qdrant client."""
    storage_path = Path(settings.VECTOR_STORE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)

    client = QdrantClient(path=str(storage_path))

    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=models.Distance.COSINE,
            ),
        )

    return client


def index_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    metadata: dict,
) -> int:
    """Store document chunks with document-level RBAC metadata."""
    if len(chunks) != len(embeddings):
        raise ValueError("Chunks and embeddings count must match")

    if not chunks:
        return 0

    required_fields = {
        "document_id",
        "department",
        "allowed_roles",
        "source_name",
    }

    missing = required_fields - metadata.keys()
    if missing:
        raise ValueError(f"Missing metadata fields: {sorted(missing)}")

    if not isinstance(metadata["allowed_roles"], list):
        raise ValueError("allowed_roles must be a list")

    if not metadata["allowed_roles"]:
        raise ValueError("At least one allowed role is required")

    client = get_qdrant_client()
    points = []

    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        if len(embedding) != settings.EMBEDDING_DIMENSION:
            raise ValueError("Embedding dimension mismatch")

        point_id = str(
            uuid5(
                NAMESPACE_URL,
                f"{metadata['document_id']}:{index}",
            )
        )

        payload = {
            **metadata,
            "chunk_index": index,
            "text": chunk,
            "is_active": True,
        }

        points.append(
            models.PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=True,
    )

    return len(points)


def search_chunks(
    query_embedding: list[float],
    department: str,
    role: str,
    limit: int | None = None,
) -> list[dict]:
    """Retrieve only chunks authorized for the requesting user."""
    if len(query_embedding) != settings.EMBEDDING_DIMENSION:
        raise ValueError("Query embedding dimension mismatch")

    if not department or not role:
        raise ValueError("Department and role are required")

    client = get_qdrant_client()

    conditions = [
        models.FieldCondition(
            key="is_active",
            match=models.MatchValue(value=True),
        ),
    ]

    # Admin access follows the existing SQL authorization policy:
    # all active documents are accessible.
    if role != "Admin":
        conditions.extend([
            models.FieldCondition(
                key="department",
                match=models.MatchValue(value=department),
            ),
            models.FieldCondition(
                key="allowed_roles",
                match=models.MatchValue(value=role),
            ),
        ])

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        query_filter=models.Filter(must=conditions),
        limit=limit or settings.RETRIEVAL_TOP_K,
        with_payload=True,
    )

    return [
        {
            "text": point.payload.get("text", ""),
            "score": point.score,
            "metadata": {
                key: value
                for key, value in point.payload.items()
                if key != "text"
            },
        }
        for point in response.points
    ]


def delete_document_chunks(document_id: str) -> None:
    """Delete all indexed chunks belonging to a document."""
    client = get_qdrant_client()

    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            )
        ),
        wait=True,
    )
