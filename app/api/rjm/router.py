"""RJM / MIRA persona program generation endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logger import app_logger
from app.api.rjm.schemas import (
    GenerateProgramRequest,
    GenerateProgramResponse,
    DocumentSyncDetail,
    SyncResponse,
    SyncSummary,
)
from app.db.db import get_session
from app.services.rjm_rag import generate_program_with_rag
from app.services.rjm_sync import sync_rjm_documents
from app.utils.responses import SuccessResponse, success_response

router = APIRouter(prefix="/v1/rjm", tags=["rjm"])


@router.post(
    "/generate",
    response_model=GenerateProgramResponse,
    summary="Generate an RJM persona program from a brief",
)
async def generate_persona_program(
    request: GenerateProgramRequest,
) -> GenerateProgramResponse:
    """Generate a single RJM-style persona program from a brief.

    This is a one-shot generation endpoint (not a chatbot).
    It:
    - Runs RAG over RJM docs (Packaging Logic, Phylum Index, Narrative Library, MIRA).
    - Calls OpenAI with a MIRA-style prompt.
    - Enforces schema + formatting to mirror RJM Packaging API / MIRA schema.
    """
    start_time = datetime.now(timezone.utc)

    try:
        app_logger.info(
            f"RJM generate request for brand={request.brand_name} "
            f"category={request.category} personas_requested={request.personas_requested}"
        )

        program_json = generate_program_with_rag(request)

        # Simple text formatting per Packaging Logic guidelines
        lines: list[str] = []
        lines.append(program_json.header)
        # Program write-up: 2 sentences, cultural and human, no tool meta.
        # Keep domain-agnostic but grounded in key identifiers and brand category.
        ki_preview = ", ".join(program_json.key_identifiers[:2]) if program_json.key_identifiers else ""
        base_context = (
            ki_preview.lower() if ki_preview else "everyday rituals and cultural moments"
        )
        sentence1 = f"Curated for those who live through {base_context}—finding meaning in how they move, gather, and express themselves."
        sentence2 = (
            "This persona program organizes those patterns into a clear, culture-led way for the brand to show up with relevance and care."
        )

        lines.append(sentence1 + " " + sentence2)
        lines.append("")

        # Key identifiers
        lines.append("🔑 Key Identifiers")
        for identifier in program_json.key_identifiers:
            lines.append(f"- {identifier}")
        lines.append("")

        # Personas
        lines.append("✨ Personas")
        for persona in program_json.personas:
            phylum = f" ({persona.phylum})" if persona.phylum else ""
            lines.append(f"- {persona.name}{phylum}")
        lines.append("")

        # Persona insights
        if program_json.persona_insights:
            lines.append("📊 Persona Insights")
            for insight in program_json.persona_insights:
                lines.append(f"- {insight}")
            lines.append("")

        # Demos
        lines.append("👥 Demos")
        core_demo = program_json.demos.get("core") or "TBD"
        secondary_demo = program_json.demos.get("secondary") or "TBD"
        lines.append(f"- Core: {core_demo}")
        lines.append(f"- Secondary: {secondary_demo}")
        lines.append("")

        # Activation plan
        if program_json.activation_plan:
            lines.append("Activation Plan")
            for step in program_json.activation_plan:
                lines.append(f"- {step}")
            lines.append("")

        # Divider
        lines.append("⸻")

        program_text = "\n".join(lines)

        return GenerateProgramResponse(
            program_json=program_json,
            program_text=program_text,
        )

    except RuntimeError as exc:
        app_logger.error(f"RJM generate unavailable: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as e:
        app_logger.error(f"RJM generate failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RJM generate failed: {str(e)}",
        )


@router.post(
    "/sync",
    response_model=SuccessResponse[SyncResponse],
    summary="Sync RJM documents into Pinecone and the local database",
)
async def sync_rjm_corpus(
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[SyncResponse]:
    """Sync RJM documents and embeddings (idempotent)."""
    try:
        result = await sync_rjm_documents(session)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:  # pragma: no cover - unexpected errors
        app_logger.error(f"RJM sync failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RJM sync failed: {str(exc)}",
        )

    summary = SyncSummary(
        total_files=result.get("total_files", 0),
        created=result.get("created", 0),
        updated=result.get("updated", 0),
        unchanged=result.get("unchanged", 0),
        deleted=result.get("deleted", 0),
        elapsed_seconds=result.get("elapsed_seconds", 0.0),
    )
    details = [DocumentSyncDetail(**detail) for detail in result.get("details", [])]

    return success_response(
        data=SyncResponse(summary=summary, details=details),
        message="RJM documents synced successfully",
    )

