"""RJM document sync service."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config.logger import app_logger
from app.config.settings import settings
from app.models.rjm_document import RJMDocument
from app.services.rjm_vector_store import (
    delete_vectors,
    embed_texts,
    get_pinecone_index,
    upsert_vectors,
)


CHUNK_DELIMITER = "\n⸻"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120  # Reserved for future use (currently split on delimiter)


def _chunk_document_text(text: str) -> List[str]:
    """Split RJM document text into logical sections."""
    text = text.strip()
    if not text:
        return []
    sections = [c.strip() for c in text.split(CHUNK_DELIMITER) if c.strip()]
    if sections:
        return sections
    sections = [c.strip() for c in text.split("\n\n") if c.strip()]
    return sections or [text]


def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _vector_ids_for_doc(doc: RJMDocument) -> List[str]:
    return [f"{doc.id}:{i}" for i in range(doc.chunk_count)]


async def sync_rjm_documents(session: AsyncSession) -> Dict[str, object]:
    """Sync RJM documents from disk into the vector store and DB."""
    docs_dir = Path(settings.RJM_DOCS_DIR).resolve()
    if not docs_dir.exists():
        raise FileNotFoundError(f"RJM docs directory not found: {docs_dir}")

    start_time = time.time()
    index = get_pinecone_index()  # Ensure client initialized (side effects only)

    result = await session.execute(select(RJMDocument))
    existing_docs = {doc.relative_path: doc for doc in result.scalars().all()}
    processed_paths: set[str] = set()

    summary = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "deleted": 0,
        "details": [],
    }

    for path in sorted(docs_dir.rglob("*.txt")):
        rel_path = path.relative_to(docs_dir).as_posix()
        processed_paths.add(rel_path)

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="latin-1")

        text = text.strip()
        content_hash = _compute_hash(text)
        doc = existing_docs.get(rel_path)

        if doc and doc.content_hash == content_hash:
            summary["unchanged"] += 1
            summary["details"].append(
                {"relative_path": rel_path, "action": "unchanged", "chunk_count": doc.chunk_count}
            )
            continue

        if doc is None:
            doc = RJMDocument(
                file_name=path.name,
                relative_path=rel_path,
                content_hash=content_hash,
                chunk_size=DEFAULT_CHUNK_SIZE,
                chunk_overlap=DEFAULT_CHUNK_OVERLAP,
            )
            existing_docs[rel_path] = doc
            action = "created"
            summary["created"] += 1
        else:
            action = "updated"
            summary["updated"] += 1

        if doc.chunk_count:
            delete_vectors(_vector_ids_for_doc(doc))

        chunks = _chunk_document_text(text)
        if not chunks:
            chunks = [text] if text else []

        embeddings = embed_texts(chunks)
        vectors = []
        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
            vectors.append(
                {
                    "id": f"{doc.id}:{i}",
                    "values": embedding,
                    "metadata": {
                        "source": rel_path,
                        "file_name": doc.file_name,
                        "text": chunk_text,
                    },
                }
            )

        # Upsert in manageable batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            upsert_vectors(vectors[i : i + batch_size])

        doc.file_name = path.name
        doc.content_hash = content_hash
        doc.chunk_count = len(chunks)
        doc.last_synced_at = datetime.now(timezone.utc)
        doc.updated_at = doc.last_synced_at
        await session.merge(doc)

        summary["details"].append(
            {"relative_path": rel_path, "action": action, "chunk_count": doc.chunk_count}
        )

    # Handle deletions (files removed from disk)
    for rel_path, doc in list(existing_docs.items()):
        if rel_path in processed_paths:
            continue
        delete_vectors(_vector_ids_for_doc(doc))
        await session.delete(doc)
        summary["deleted"] += 1
        summary["details"].append(
            {"relative_path": rel_path, "action": "deleted", "chunk_count": doc.chunk_count}
        )

    await session.commit()

    elapsed = time.time() - start_time
    summary["elapsed_seconds"] = round(elapsed, 2)
    summary["total_files"] = len(processed_paths)

    app_logger.info(
        "RJM sync complete - created=%s updated=%s unchanged=%s deleted=%s elapsed=%.2fs",
        summary["created"],
        summary["updated"],
        summary["unchanged"],
        summary["deleted"],
        summary["elapsed_seconds"],
    )

    return summary


