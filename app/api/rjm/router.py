"""RJM / MIRA persona program generation endpoints."""

from datetime import datetime, timezone
from typing import List, Set

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logger import app_logger
from app.api.rjm.schemas import (
    GenerateProgramRequest,
    GenerateProgramResponse,
    DocumentSyncDetail,
    SyncResponse,
    SyncSummary,
    Persona,
)
from app.db.db import get_session
from app.services.rjm_rag import generate_program_with_rag
from app.services.rjm_sync import sync_rjm_documents
from app.utils.responses import SuccessResponse, success_response
from app.services.rjm_ingredient_canon import (
    ALL_GENERATIONAL_NAMES,
    GENERATIONS,
    get_category_personas,
    get_dual_anchors,
    infer_category as infer_ad_category,
    is_local_brief,
    register_personas_for_rotation,
    register_generational_for_rotation,
    is_persona_recent,
    is_generational_recent,
    detect_multicultural_lineage,
    get_multicultural_expressions,
)

router = APIRouter(prefix="/v1/rjm", tags=["rjm"])


def _clean_highlight(name: str, highlight: str) -> str:
    """Remove persona name prefix from highlight if LLM included it.
    
    Handles patterns like:
    - "Bargain Hunter → Seeks deals..." -> "Seeks deals..."
    - "Bargain Hunter: Seeks deals..." -> "Seeks deals..."
    - "Bargain Hunter - Seeks deals..." -> "Seeks deals..."
    """
    if not highlight:
        return highlight
    
    # Check for common patterns where LLM includes the name
    patterns = [
        f"{name} → ",
        f"{name} -> ",
        f"{name}: ",
        f"{name} - ",
        f"{name}→",
        f"{name}:",
    ]
    
    for pattern in patterns:
        if highlight.startswith(pattern):
            return highlight[len(pattern):].strip()
    
    return highlight


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
            f"RJM generate request for brand={request.brand_name}"
        )

        program_json = generate_program_with_rag(request)
        
        detected_category = (
            program_json.advertising_category
            or infer_ad_category(f"{request.brand_name} {request.brief}")
        )
        category_persona_pool = get_category_personas(detected_category)
        
        # Use dual anchors for brands that span multiple categories
        category_anchors = get_dual_anchors(request.brand_name, detected_category)

        # Packaging text formatting per MIRA Packaging Implementation Spec
        lines: list[str] = []

        # 1. Header + Write-Up
        lines.append(request.brand_name)
        lines.append("Persona Program")
        lines.append("⸻")

        # Strip trailing periods from key identifiers for smooth sentence flow
        clean_ki = [ki.rstrip(".").strip() for ki in (program_json.key_identifiers or [])[:2]]
        ki_preview = ", ".join(clean_ki) if clean_ki else ""
        base_context = (
            ki_preview.lower() if ki_preview else "beauty, ritual, culture, and everyday expression"
        )
        sentence1 = (
            f"Curated for those who turn {base_context} into meaning, memory, and momentum."
        )
        sentence2 = (
            f"This {request.brand_name} program organizes those patterns into a clear, strategist-led framework for how the brand shows up in culture."
        )
        write_up = f"{sentence1} {sentence2}"
        lines.append(write_up)
        lines.append("")

        # 2. Key Identifiers (4–5 bullets, real bullet glyphs)
        lines.append("🔑 Key Identifiers")
        key_ids = list(program_json.key_identifiers or [])
        if len(key_ids) > 5:
            key_ids = key_ids[:5]
        while len(key_ids) < 4 and key_ids:
            key_ids.append(key_ids[-1])
        for identifier in key_ids:
            lines.append(f"• {identifier}")
        lines.append("")

        # 3. Persona Highlights (4 total: aim for 3 core + 1 generational)
        lines.append("✨ Persona Highlights")
        personas_with_highlight = [p for p in program_json.personas if getattr(p, "highlight", None)]

        core_highlight_candidates = [
            p for p in personas_with_highlight if p.name not in ALL_GENERATIONAL_NAMES
        ]

        highlights: list = []
        # Prefer up to 3 core highlights
        highlights.extend(core_highlight_candidates[:3])

        # Add 1 generational highlight if available (use LLM-generated highlight)
        generational_segments = program_json.generational_segments or []
        if generational_segments and len(highlights) < 4:
            # Use the first generational segment with its LLM-generated highlight
            gen_segment = generational_segments[0]
            highlights.append(gen_segment)  # GenerationalSegment object has name and highlight

        # If still fewer than 4, backfill with remaining core personas
        if len(highlights) < 4:
            remaining_core = [
                p
                for p in program_json.personas
                if p not in highlights and p.name not in ALL_GENERATIONAL_NAMES
            ]
            for p in remaining_core:
                if len(highlights) >= 4:
                    break
                highlights.append(p)

        selected_highlights = highlights[:4]
        highlight_names = []
        for item in selected_highlights:
            if hasattr(item, 'highlight') and item.highlight:
                # Clean the highlight in case LLM included the persona name
                clean_hl = _clean_highlight(item.name, item.highlight)
                lines.append(f"{item.name} → {clean_hl}")
                highlight_names.append(item.name)
            else:
                # Simple fallback highlight line if model did not provide one
                lines.append(
                    f"{item.name} → Brings the brand to life through everyday cultural moments."
                )
                highlight_names.append(item.name)
        lines.append("")

        # 4. Persona Insights (2 total, with % – already enforced in ProgramJSON)
        lines.append("📊 Persona Insights")
        insights = list(program_json.persona_insights or [])
        for insight in insights:
            lines.append(f"• {insight}")
        lines.append("")

        # 5. Demos (Core + Secondary + optional Broad)
        lines.append("👥 Demos")
        core_demo = program_json.demos.get("core") or "Adults 25–54"
        secondary_demo = program_json.demos.get("secondary") or "Adults 18+"
        lines.append(f"• Core : {core_demo}")
        lines.append(f"• Secondary : {secondary_demo}")
        broad_demo = program_json.demos.get("broad_demo")
        if broad_demo:
            lines.append(f"• Broad : {broad_demo}")
        lines.append("")

        # 6. Persona Portfolio (~20 total with anchors & generational mix)
        core_personas = [
            p.name for p in program_json.personas if p.name not in ALL_GENERATIONAL_NAMES
        ]
        core_personas = _dedupe_preserve(core_personas)

        core_personas = _fill_persona_list(
            result=core_personas,
            pool=category_persona_pool,
            target=15,
            excluded=ALL_GENERATIONAL_NAMES,
            recent_checker=is_persona_recent,
        )

        # Use the generational segments from the model (extract names from GenerationalSegment objects)
        generational_names = [seg.name for seg in generational_segments[:4]]
        
        # Ensure we have 4 generational segments (backfill if needed)
        if len(generational_names) < 4:
            from app.services.rjm_ingredient_canon import GENERATIONS_BY_COHORT
            for cohort, segments in GENERATIONS_BY_COHORT.items():
                if len(generational_names) >= 4:
                    break
                has_cohort = any(name.startswith(cohort) for name in generational_names)
                if not has_cohort and segments:
                    # Pick one that hasn't been used recently
                    for seg in segments:
                        if not is_generational_recent(seg):
                            generational_names.append(seg)
                            break
                    else:
                        generational_names.append(segments[0])

        # Get anchors (handles dual-anchor brands like L'Oréal)
        anchors = category_anchors[:2]

        final_core = core_personas[:15]
        final_generational = generational_names[:4]
        final_portfolio = final_core + anchors + final_generational

        register_personas_for_rotation([name for name in final_core if name not in highlight_names])
        register_generational_for_rotation(final_generational)

        lines.append("📍 Persona Portfolio")
        lines.append(" · ".join(final_portfolio))
        lines.append("")

        # 7. Activation Plan (verbatim)
        if program_json.activation_plan:
            lines.append("🧭 Activation Plan")
            for step in program_json.activation_plan:
                lines.append(f"• {step}")
            lines.append("")

        # Optional Local Strategy Addendum for DMA/state/regional briefs
        if is_local_brief(request.brief):
            lines.append("📍 Local Strategy")
            lines.append(
                "Apply Local Culture segments by DMA alongside the core program so each market reflects its own character while staying tied to the overarching brand framework."
            )
            lines.append("")

        # Optional Multicultural Addendum if brief targets specific cultural lineage
        multicultural_lineage = detect_multicultural_lineage(request.brief)
        if multicultural_lineage:
            expressions = get_multicultural_expressions(multicultural_lineage)
            if expressions:
                lines.append("🌍 Multicultural Layer")
                lines.append(
                    f"Apply {multicultural_lineage} Multicultural Expressions alongside the core program: {', '.join(expressions[:3])}."
                )
                lines.append("")

        # 8. Divider
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


def _dedupe_preserve(names: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for name in names:
        if name and name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def _fill_persona_list(
    result: List[str],
    pool: List[str],
    target: int,
    excluded: Set[str],
    recent_checker=None,
) -> List[str]:
    output = _dedupe_preserve(result)
    excluded_set = set(excluded or set())

    def append(skip_recent: bool) -> None:
        for name in pool:
            if len(output) >= target:
                break
            if not name or name in excluded_set or name in output:
                continue
            if skip_recent and recent_checker and recent_checker(name):
                continue
            output.append(name)

    append(skip_recent=True)
    if len(output) < target:
        append(skip_recent=False)
    return output
