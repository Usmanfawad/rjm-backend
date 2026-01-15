"""RJM document sync service using Supabase REST API."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

from app.config.logger import app_logger
from app.config.settings import settings
from app.db.supabase_db import get_records, insert_record, update_record, delete_record
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


def _vector_ids_for_doc(doc_id: str, chunk_count: int) -> List[str]:
    return [f"{doc_id}:{i}" for i in range(chunk_count)]


async def sync_rjm_documents() -> Dict[str, object]:
    """Sync RJM documents from disk into the vector store and Supabase.
    
    Uses Supabase REST API for database operations.
    """
    docs_dir = Path(settings.RJM_DOCS_DIR).resolve()
    if not docs_dir.exists():
        raise FileNotFoundError(f"RJM docs directory not found: {docs_dir}")

    start_time = time.time()
    index = get_pinecone_index()  # Ensure client initialized (side effects only)

    # Get existing documents from Supabase
    existing_docs_list = await get_records("rjm_documents")
    existing_docs = {doc["relative_path"]: doc for doc in existing_docs_list}
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

        if doc and doc.get("content_hash") == content_hash:
            summary["unchanged"] += 1
            summary["details"].append(
                {"relative_path": rel_path, "action": "unchanged", "chunk_count": doc.get("chunk_count", 0)}
            )
            continue

        if doc is None:
            # Create new document
            doc_id = str(uuid4())
            doc = {
                "id": doc_id,
                "file_name": path.name,
                "relative_path": rel_path,
                "content_hash": content_hash,
                "chunk_size": DEFAULT_CHUNK_SIZE,
                "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
                "chunk_count": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            existing_docs[rel_path] = doc
            action = "created"
            summary["created"] += 1
        else:
            action = "updated"
            summary["updated"] += 1
            doc_id = doc["id"]

        # Delete old vectors if updating
        old_chunk_count = doc.get("chunk_count", 0)
        if old_chunk_count:
            delete_vectors(_vector_ids_for_doc(doc_id, old_chunk_count))

        chunks = _chunk_document_text(text)
        if not chunks:
            chunks = [text] if text else []

        embeddings = embed_texts(chunks)
        vectors = []
        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
            vectors.append(
                {
                    "id": f"{doc_id}:{i}",
                    "values": embedding,
                    "metadata": {
                        "source": rel_path,
                        "file_name": path.name,
                        "text": chunk_text,
                    },
                }
            )

        # Upsert in manageable batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            upsert_vectors(vectors[i : i + batch_size])

        # Update or insert document in Supabase
        now = datetime.now(timezone.utc).isoformat()
        doc_data = {
            "file_name": path.name,
            "content_hash": content_hash,
            "chunk_count": len(chunks),
            "updated_at": now,
        }

        if action == "created":
            doc_data["id"] = doc_id
            doc_data["relative_path"] = rel_path
            doc_data["chunk_size"] = DEFAULT_CHUNK_SIZE
            doc_data["chunk_overlap"] = DEFAULT_CHUNK_OVERLAP
            await insert_record("rjm_documents", doc_data)
        else:
            await update_record("rjm_documents", doc_id, doc_data)

        summary["details"].append(
            {"relative_path": rel_path, "action": action, "chunk_count": len(chunks)}
        )

    # Handle deletions (files removed from disk)
    for rel_path, doc in list(existing_docs.items()):
        if rel_path in processed_paths:
            continue
        doc_id = doc["id"]
        chunk_count = doc.get("chunk_count", 0)
        delete_vectors(_vector_ids_for_doc(doc_id, chunk_count))
        await delete_record("rjm_documents", doc_id)
        summary["deleted"] += 1
        summary["details"].append(
            {"relative_path": rel_path, "action": "deleted", "chunk_count": chunk_count}
        )

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
