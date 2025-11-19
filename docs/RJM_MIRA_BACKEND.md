## RJM MIRA Backend Overview

This backend implements a lightweight version of RJM's MIRA engine on top of the RJM backend core.

It:

- Accepts **brand briefs** and structured inputs.
- Uses **OpenAI + Pinecone** over the RJM document corpus.
- Returns **Persona Programs** that follow RJM Packaging Logic, Phylum Index, and Narrative Library rules.

---

## Endpoints

- **POST `/v1/rjm/sync`**
  - Reads all `.txt` files under `RJM_DOCS_DIR`.
  - Stores metadata + hashes in the `rjm_documents` table (SQLModel).
  - Embeds changed documents and upserts vectors into Pinecone (namespace `rjm-docs`).
  - Deletes stale vectors if a file is removed.

- **POST `/v1/rjm/generate`**
  - **Purpose**: Generate a single RJM Persona Program.
  - **Request body** (`GenerateProgramRequest`):
    - `brief` – brand brief or intuitive text prompt.
    - `brand_name` – advertiser / client name.
    - `category` – ad vertical (QSR, Auto, Finance, Retail, etc.).
    - `personas_requested` – integer 6–20.
    - `filters`:
      - `local_culture` – bool.
      - `generational` – bool.
      - `multicultural` – bool.
  - **Response** (`GenerateProgramResponse`):
    - `program_json` (`ProgramJSON` – aligned with RJM Packaging API v1 output schema):
      - `header` – `[Brand] | Persona Framework`.
      - `key_identifiers` – 3–6 macro themes.
      - `personas` – 6–20 objects `{ name, category, phylum }`.
      - `persona_insights` – up to 3 bullets.
      - `demos` – `{ core, secondary }`.
      - `activation_plan` – 3–5 bullets.
    - `program_text` – formatted text version:
      - Header + 1–2 sentence write-up (RJM voice).
      - Key Identifiers (🔑).
      - Personas (✨).
      - Persona Insights (📊).
      - Demos (👥).
      - Activation plan.
      - Divider `⸻`.

---

## RAG + MIRA flow

Implementation lives in:

- `app/services/rjm_rag.py`
- `app/api/rjm/router.py`
- `app/api/rjm/schemas.py`

### High-level steps

1. **Sync / Indexing (`/v1/rjm/sync`)**
   - Load RJM docs from `RJM_DOCS_DIR`:
     - `Packaging Logic MASTER 10-22-25.txt`
     - `Phylum Index MASTER 10-22-25.txt`
     - `Narrative Library 10-23-25.txt`
     - `MIRA/RJM MIRA_Reasoning Architecture.txt`
     - `MIRA/MIRA_Developer Integration.txt`
     - `RJM API PACKAGE   (10.10.25)/RJM API Overview.txt`
     - `RJM API PACKAGE   (10.10.25)/RJM API Integration Guide.txt`
   - Split into chunks and embed with OpenAI embeddings.
   - Upsert into Pinecone index (`PINECONE_INDEX_NAME`, default `rjm-mira-docs`), tracking hashes in `rjm_documents`.

2. **Retrieval**
   - For each `/v1/rjm/generate` request:
     - Build a query string from brief + brand + category + filters.
     - Embed the query.
     - Query Pinecone for top-k relevant RJM chunks.

3. **Generation (MIRA-style)**
   - Compose a system message that encodes:
     - MIRA reasoning steps (brief → phyla → personas → identifiers → narrative → activation).
     - Packaging Logic formatting rules.
   - Send a chat completion request to `OPENAI_MODEL` with:
     - System message (MIRA behavior + schema instructions).
     - User message (RJM context snippets + brand request).
   - Expect **strict JSON** with keys:
     - `header`, `key_identifiers`, `personas`, `persona_insights`, `demos`, `activation_plan`.
   - Parse JSON into `ProgramJSON` (with fallbacks if parsing fails).
   - Compose a human-readable `program_text` that mirrors Packaging Logic.

---

## Configuration summary

Key environment variables (see `app/config/settings.py`):

- **OpenAI**
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL` (e.g., `gpt-4o-mini`)
  - `OPENAI_EMBEDDING_MODEL` (e.g., `text-embedding-3-small`)

- **Pinecone**
  - `PINECONE_API_KEY`
  - `PINECONE_INDEX_NAME` (default `rjm-mira-docs`)
  - `PINECONE_REGION` (default `us-east-1`)

- **RJM docs**
  - `RJM_DOCS_DIR` – base directory containing RJM `.txt` files (default `rjm_docs`).

- **Database**
  - `DATABASE_URL` – optional; if omitted, falls back to `sqlite+aiosqlite:///./local.db`.

---

## Notes / TODOs for refinement

- Tighten prompt and persona selection so all personas are strictly from the RJM canon (Phylum Index + Narrative Library).
- Add automated tests for:
  - JSON schema compliance.
  - Persona count bounds (6–20).
  - Section order in `program_text`.
- Expand sync to support parallel chunking and configurable namespaces.


