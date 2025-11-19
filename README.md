## RJM MIRA Backend (built on RJM Backend Core)

FastAPI backend that turns RJM brand briefs into structured Persona Programs using:

- **OpenAI** (chat + embeddings) as the MIRA reasoning engine
- **Pinecone** as a vector store over RJM documents (Packaging Logic, Phylum Index, Narrative Library, MIRA docs)
- **SQLite by default** (easy to swap to Postgres/Supabase later)

The original core structure (auth, audit, DB) is preserved; this project adds RJM-specific `/v1/rjm/sync` and `/v1/rjm/generate` endpoints and RAG pipeline.

## Setup

1. **Create and activate a Python 3.12 environment**.
2. **Install dependencies**:

```bash
pip install -e .
```

3. **Copy `.env.example` to `.env`** and fill in the values listed below.

```bash
cp .env.example .env
```

### Required configuration (for RJM)

- **OpenAI**

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

- **Pinecone**

```env
PINECONE_API_KEY=pc-...
PINECONE_INDEX_NAME=rjm-mira-docs
PINECONE_REGION=us-east-1
```

- **RJM document corpus**
- **Local Auth Fallback (optional)**

When Supabase credentials are not provided, `/v1/auth/login` falls back to a simple
local auth mode that issues short-lived JWTs. Configure the secret + expiration if needed:

```env
LOCAL_AUTH_SECRET=super-secret-change-me
LOCAL_AUTH_TOKEN_EXP_SECONDS=3600
```


Point this to the directory that contains your converted RJM `.txt` files:

```env
RJM_DOCS_DIR=rjm_docs
```

The code expects files such as:

- `Packaging Logic MASTER 10-22-25.txt`
- `Phylum Index MASTER 10-22-25.txt`
- `Narrative Library 10-23-25.txt`
- `MIRA/RJM MIRA_Reasoning Architecture.txt`
- `MIRA/MIRA_Developer Integration.txt`
- `RJM API PACKAGE   (10.10.25)/RJM API Overview.txt`
- `RJM API PACKAGE   (10.10.25)/RJM API Integration Guide.txt`

### Database configuration

By default, if you **do not** set `DATABASE_URL` or Supabase DB variables, the app will fall back to a local SQLite file:

```env
DATABASE_URL=
SUPABASE_DATABASE_HOST=
SUPABASE_DATABASE_PASSWORD=
# Optional: override default local DB path
LOCAL_SQLITE_PATH=sqlite+aiosqlite:///./local.db
```

If `LOCAL_SQLITE_PATH` is set and `DATABASE_URL` / Supabase are empty, that value is used
as the SQLite connection URL (you can point it anywhere on disk).

To use Postgres (e.g., Supabase) instead, set:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxx.supabase.co:5432/postgres?sslmode=require
```

or configure the `SUPABASE_DATABASE_*` fields (see `supabase/README.md` for details).

### Supabase Auth (optional – only needed if you use `/auth` endpoints)

If you plan to use the existing Supabase-based auth flow, follow `supabase/README.md` for:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

Otherwise, you can ignore auth endpoints during early RJM development.

## Running

```bash
uvicorn app.main:app --reload
```

The OpenAPI docs will be available at `/docs`.
On startup the app seeds a local admin user (only used in local auth mode):

- Email: `admin@test.com`
- Password: `Password123!`

## Key endpoints

- **Health**
  - `/` – root info
  - `/status` – build + environment info
  - `/health/db` – DB health (SQLite/Postgres)

- **RJM / MIRA**
  - `POST /v1/rjm/sync`
    - Reads the `.txt` corpus from `RJM_DOCS_DIR`
    - Stores per-document metadata in the `rjm_documents` table
    - Generates embeddings and upserts them into Pinecone (only for new/changed files)
  - `POST /v1/rjm/generate`
    - Body: `GenerateProgramRequest` (brief, brand_name, category, personas_requested, filters)
    - Returns: `GenerateProgramResponse`:
      - `program_json` – strict JSON persona program
      - `program_text` – formatted text version matching Packaging Logic

> ⚠️ Run `/v1/rjm/sync` at least once (and any time the docs change) before calling `/v1/rjm/generate`.

## How the RJM pipeline works

1. **Sync (`/v1/rjm/sync`)**
   - Scans every `.txt` file under `RJM_DOCS_DIR`.
   - Computes a SHA-256 hash for change detection and stores it in `rjm_documents`.
   - Splits the file on `⸻` (or blank lines), embeds chunks with OpenAI, and upserts vectors into Pinecone (namespace `rjm-docs`).
   - Deletes stale vectors/rows if a file is removed.
2. **Generate (`/v1/rjm/generate`)**
   - Embeds the brief + filters and queries Pinecone for the top-k chunks.
   - Sends the retrieved context + brief into OpenAI with the MIRA prompt.
   - Parses the JSON reply into `ProgramJSON` and mirrors it as formatted text.

For more detail, see `docs/RJM_MIRA_BACKEND.md`.

