"""Shared helpers for RJM vector store (OpenAI + Pinecone)."""

from __future__ import annotations

from typing import List, Sequence

from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

from app.config.logger import app_logger
from app.config.settings import settings

_openai_client: OpenAI | None = None
_pinecone_client: Pinecone | None = None
_pinecone_index = None

PINECONE_NAMESPACE = "rjm-docs"


def get_openai_client() -> OpenAI:
    """Return a singleton OpenAI client."""
    global _openai_client
    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be configured")
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        app_logger.info("OpenAI client initialized")
    return _openai_client


def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    """Create embeddings for a list of texts."""
    if not texts:
        return []
    client = get_openai_client()
    response = client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=list(texts),
    )
    return [item.embedding for item in response.data]


def get_pinecone_client() -> Pinecone:
    """Return a singleton Pinecone client."""
    global _pinecone_client
    if _pinecone_client is None:
        if not settings.PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY must be configured")
        _pinecone_client = Pinecone(api_key=settings.PINECONE_API_KEY)
        app_logger.info("Pinecone client initialized")
    return _pinecone_client


def get_pinecone_index():
    """Return the Pinecone index for RJM docs, creating it if necessary."""
    global _pinecone_index
    if _pinecone_index is not None:
        return _pinecone_index

    pc = get_pinecone_client()
    index_name = settings.PINECONE_INDEX_NAME

    existing = [idx["name"] for idx in pc.list_indexes()]
    if index_name not in existing:
        app_logger.info(f"Creating Pinecone index '{index_name}' for RJM docs")
        sample_embedding = embed_texts(["RJM init vector dimension sample"])[0]
        dimension = len(sample_embedding)
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region=settings.PINECONE_REGION or "us-east-1",
            ),
        )

    _pinecone_index = pc.Index(index_name)
    app_logger.info(f"Using Pinecone index '{index_name}'")
    return _pinecone_index


def describe_index_stats():
    """Return Pinecone index stats for the RJM namespace."""
    index = get_pinecone_index()
    return index.describe_index_stats()


def upsert_vectors(vectors: List[dict]) -> None:
    """Upsert vectors into Pinecone under the RJM namespace."""
    if not vectors:
        return
    index = get_pinecone_index()
    index.upsert(vectors=vectors, namespace=PINECONE_NAMESPACE)


def delete_vectors(vector_ids: Sequence[str]) -> None:
    """Delete vectors by ID from the RJM namespace."""
    if not vector_ids:
        return
    index = get_pinecone_index()
    index.delete(ids=list(vector_ids), namespace=PINECONE_NAMESPACE)


