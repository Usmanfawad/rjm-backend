"""RJM / MIRA persona program generation endpoints."""

import json
from datetime import datetime, timezone
from typing import List, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.config.logger import app_logger
from app.api.rjm.schemas import (
    GenerateProgramRequest,
    GenerateProgramResponse,
    DocumentSyncDetail,
    SyncResponse,
    SyncSummary,
    MiraChatRequest,
    MiraChatResponse,
    TranscriptionResponse,
    PersonaGenerationResponse,
    PersonaGenerationListResponse,
    ChatSessionSummary,
    ChatSessionListResponse,
    ChatMessageResponse,
    ChatSessionDetailResponse,
)
from app.db.supabase_db import insert_record, get_records
from app.services.mira_chat import handle_chat_turn
from app.services.rjm_rag import generate_program_with_rag
from app.services.rjm_sync import sync_rjm_documents
from app.utils.responses import SuccessResponse, success_response
from app.utils.auth import get_current_user_id, require_auth
from app.services.rjm_ingredient_canon import (
    ALL_GENERATIONAL_NAMES,
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
    response_model=SuccessResponse[GenerateProgramResponse],
    summary="Generate an RJM persona program from a brief",
)
async def generate_persona_program(
    request: GenerateProgramRequest,
    user_id: Optional[str] = Depends(get_current_user_id),
) -> SuccessResponse[GenerateProgramResponse]:
    """Generate a single RJM-style persona program from a brief.

    This is a one-shot generation endpoint (not a chatbot).
    It:
    - Runs RAG over RJM docs (Packaging Logic, Phylum Index, Narrative Library, MIRA).
    - Calls OpenAI with a MIRA-style prompt.
    - Enforces schema + formatting to mirror RJM Packaging API / MIRA schema.
    - Saves the generation to the database if user is authenticated.
    """
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

        # Save the generation to Supabase if user is authenticated
        if user_id:
            try:
                from uuid import uuid4
                gen_id = str(uuid4())
                await insert_record("persona_generations", {
                    "id": gen_id,
                    "user_id": user_id,
                    "brand_name": request.brand_name,
                    "brief": request.brief,
                    "program_text": program_text,
                    "program_json": program_json.model_dump_json(),
                    "advertising_category": detected_category,
                    "source": "generator",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                app_logger.info(
                    f"Saved persona generation id={gen_id} for user={user_id}"
                )
            except Exception as save_error:
                app_logger.warning(
                    f"Failed to save persona generation: {save_error}"
                )
                # Don't fail the request if save fails

        return success_response(
            data=GenerateProgramResponse(
                program_json=program_json,
                program_text=program_text,
            ),
            message="Persona program generated successfully",
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
async def sync_rjm_corpus() -> SuccessResponse[SyncResponse]:
    """Sync RJM documents and embeddings (idempotent)."""
    try:
        result = await sync_rjm_documents()
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


@router.post(
    "/chat",
    response_model=SuccessResponse[MiraChatResponse],
    summary="MIRA conversational endpoint (behavioral engine + packaging bridge)",
)
async def mira_chat_turn(
    request: MiraChatRequest,
    user_id: Optional[str] = Depends(get_current_user_id),
) -> SuccessResponse[MiraChatResponse]:
    """
    Single-turn MIRA chat endpoint.

    This endpoint:
    - Uses the Behavioral Engine spec to interpret the current interaction state.
    - Bridges into the existing Packaging / RAG pipeline when a Persona Program is needed.
    - Returns a strategist-style reply plus the next behavioral state id.
    - Saves any generated persona programs to the database if user is authenticated.
    - Persists all chat messages to the database for future retrieval and resumption.

    The client is responsible for:
    - Sending the `state` from the previous response (or omitting it for a fresh GREETING).
    - Providing `brand_name` and `brief` when ready to generate a program.
    - Optionally sending `session_id` to continue a previous conversation.
    """
    # Capture state before processing
    state_before = request.state or "STATE_GREETING"
    
    # Get user message content
    user_message = ""
    if request.messages:
        user_msgs = [m for m in request.messages if m.role == "user"]
        if user_msgs:
            user_message = user_msgs[-1].content
    
    result = handle_chat_turn(request, user_id=user_id)
    
    # Persist chat messages to database if user is authenticated
    if user_id and result.session_id:
        try:
            from app.services.chat_persistence import persist_chat_turn
            from app.services.mira_session import get_session
            
            # Get session state for brand/brief/category
            _, session_state = get_session(result.session_id)
            
            await persist_chat_turn(
                session_id=result.session_id,
                user_id=user_id,
                user_message=user_message,
                assistant_reply=result.reply,
                state_before=state_before,
                state_after=result.state,
                brand_name=session_state.brand_name or request.brand_name,
                brief=session_state.brief or request.brief,
                category=session_state.category,
            )
        except Exception as persist_error:
            app_logger.warning(f"Failed to persist chat turn: {persist_error}")
    
    # Check if a generation was created and save it to Supabase
    if result.generation_data and user_id:
        try:
            from uuid import uuid4
            gen_data = result.generation_data
            gen_id = str(uuid4())
            await insert_record("persona_generations", {
                "id": gen_id,
                "user_id": user_id,
                "brand_name": gen_data["brand_name"],
                "brief": gen_data["brief"],
                "program_text": gen_data["program_text"],
                "program_json": gen_data["program_json"],
                "advertising_category": gen_data.get("advertising_category"),
                "source": "chat",
                "session_id": result.session_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            app_logger.info(
                f"Saved persona generation from chat id={gen_id} for user={user_id}"
            )
        except Exception as save_error:
            app_logger.warning(
                f"Failed to save persona generation from chat: {save_error}"
            )
    
    return success_response(data=result, message="Chat response generated")


# Maximum file size: 25 MB (OpenAI limit)
MAX_AUDIO_SIZE = 25 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/mp3",
    "audio/mpeg",
    "audio/mp4",
    "audio/m4a",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "video/webm",  # Some browsers send webm audio as video/webm
}


@router.post(
    "/transcribe",
    response_model=SuccessResponse[TranscriptionResponse],
    summary="Transcribe audio to text using OpenAI Speech-to-Text",
)
async def transcribe_audio_endpoint(
    file: UploadFile = File(..., description="Audio file to transcribe (mp3, mp4, mpeg, m4a, wav, webm)"),
    language: Optional[str] = Form(default=None, description="Optional language code (ISO 639-1) e.g., 'en', 'es'"),
    prompt: Optional[str] = Form(default=None, description="Optional prompt to guide transcription"),
) -> SuccessResponse[TranscriptionResponse]:
    """Transcribe an audio file to text.

    This endpoint accepts audio files and returns the transcribed text.
    Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, webm
    Maximum file size: 25 MB

    The transcribed text can be edited by the user before sending to the chat.
    """
    from app.services.transcription import transcribe_audio

    # Validate content type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_AUDIO_TYPES:
        app_logger.warning(f"Invalid audio content type: {content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid audio format. Supported formats: mp3, mp4, mpeg, m4a, wav, webm. Got: {content_type}",
        )

    # Read file content
    try:
        audio_data = await file.read()
    except Exception as e:
        app_logger.error(f"Failed to read uploaded audio file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded audio file.",
        )

    # Validate file size
    if len(audio_data) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file too large. Maximum size is 25 MB. Got: {len(audio_data) / (1024 * 1024):.2f} MB",
        )

    if len(audio_data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is empty.",
        )

    # Get filename for format detection
    filename = file.filename or "audio.webm"

    try:
        text = transcribe_audio(
            audio_data=audio_data,
            filename=filename,
            language=language,
            prompt=prompt,
        )
        return success_response(
            data=TranscriptionResponse(text=text),
            message="Audio transcribed successfully",
        )
    except RuntimeError as e:
        app_logger.error(f"Transcription service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        app_logger.error(f"Unexpected transcription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )


@router.get(
    "/generations",
    response_model=SuccessResponse[PersonaGenerationListResponse],
    summary="List all persona generations for the current user",
)
async def list_persona_generations(
    user_id: str = Depends(require_auth),
    limit: int = 50,
    offset: int = 0,
) -> SuccessResponse[PersonaGenerationListResponse]:
    """List all persona program generations for the authenticated user.

    Returns a list of generated persona programs ordered by creation date (newest first).
    """
    try:
        # Query generations for this user via Supabase REST API
        generations = await get_records(
            "persona_generations",
            filters={"user_id": user_id},
            limit=limit,
            order_by="created_at",
            ascending=False,
        )

        total = len(generations)

        # Convert to response format
        generation_responses = []
        for gen in generations:
            try:
                program_json_data = json.loads(gen.get("program_json", "")) if gen.get("program_json") else None
            except json.JSONDecodeError:
                program_json_data = None

            generation_responses.append(
                PersonaGenerationResponse(
                    id=str(gen["id"]),
                    brand_name=gen.get("brand_name", ""),
                    brief=gen.get("brief", ""),
                    program_text=gen.get("program_text", ""),
                    program_json=program_json_data,
                    advertising_category=gen.get("advertising_category"),
                    source=gen.get("source"),
                    created_at=gen.get("created_at", ""),
                )
            )

        return success_response(
            data=PersonaGenerationListResponse(
                generations=generation_responses,
                total=total,
            ),
            message=f"Found {total} persona generations",
        )

    except Exception as e:
        app_logger.error(f"Failed to list persona generations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list persona generations: {str(e)}",
        )


@router.get(
    "/generations/{generation_id}",
    response_model=SuccessResponse[PersonaGenerationResponse],
    summary="Get a specific persona generation by ID",
)
async def get_persona_generation(
    generation_id: str,
    user_id: str = Depends(require_auth),
) -> SuccessResponse[PersonaGenerationResponse]:
    """Get a specific persona program generation by ID.

    Only returns the generation if it belongs to the authenticated user.
    """
    try:
        # Validate UUID format
        UUID(generation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid generation ID format",
        )

    try:
        # Query via Supabase REST API
        generations = await get_records(
            "persona_generations",
            filters={"id": generation_id, "user_id": user_id},
            limit=1,
        )

        if not generations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Persona generation not found",
            )

        gen = generations[0]

        try:
            program_json_data = json.loads(gen.get("program_json", "")) if gen.get("program_json") else None
        except json.JSONDecodeError:
            program_json_data = None

        return success_response(
            data=PersonaGenerationResponse(
                id=str(gen["id"]),
                brand_name=gen.get("brand_name", ""),
                brief=gen.get("brief", ""),
                program_text=gen.get("program_text", ""),
                program_json=program_json_data,
                advertising_category=gen.get("advertising_category"),
                source=gen.get("source"),
                created_at=gen.get("created_at", ""),
            ),
            message="Persona generation retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Failed to get persona generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get persona generation: {str(e)}",
        )


# ============================================
# Chat Session Endpoints (History & Resumption)
# ============================================

@router.get(
    "/sessions",
    response_model=SuccessResponse[ChatSessionListResponse],
    summary="List all chat sessions for the current user",
)
async def list_chat_sessions(
    user_id: str = Depends(require_auth),
    limit: int = 50,
    offset: int = 0,
) -> SuccessResponse[ChatSessionListResponse]:
    """List all chat sessions for the authenticated user.

    Returns sessions ordered by last activity (most recent first).
    Use this to display chat history in the UI.
    """
    try:
        from app.services.chat_persistence import get_user_chat_sessions
        
        sessions = await get_user_chat_sessions(user_id, limit=limit, offset=offset)
        
        session_summaries = [
            ChatSessionSummary(
                id=str(s["id"]),
                title=s.get("title"),
                brand_name=s.get("brand_name"),
                category=s.get("category"),
                message_count=s.get("message_count", 0),
                current_state=s.get("current_state", "STATE_GREETING"),
                created_at=s.get("created_at", ""),
                updated_at=s.get("updated_at", ""),
            )
            for s in sessions
        ]
        
        return success_response(
            data=ChatSessionListResponse(
                sessions=session_summaries,
                total=len(session_summaries),
            ),
            message=f"Found {len(session_summaries)} chat sessions",
        )
        
    except Exception as e:
        app_logger.error(f"Failed to list chat sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list chat sessions: {str(e)}",
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SuccessResponse[ChatSessionDetailResponse],
    summary="Get a chat session with all messages",
)
async def get_chat_session(
    session_id: str,
    user_id: str = Depends(require_auth),
) -> SuccessResponse[ChatSessionDetailResponse]:
    """Get a specific chat session with all its messages.

    Use this to display the full conversation history when a user
    selects a past chat to view or resume.
    """
    try:
        # Validate UUID format
        UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    try:
        from app.services.chat_persistence import get_chat_session_detail
        
        session = await get_chat_session_detail(session_id, user_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )
        
        messages = [
            ChatMessageResponse(
                id=str(m["id"]),
                role=m["role"],
                content=m["content"],
                state_before=m.get("state_before"),
                state_after=m.get("state_after"),
                created_at=m.get("created_at", ""),
            )
            for m in session.get("messages", [])
        ]
        
        return success_response(
            data=ChatSessionDetailResponse(
                id=str(session["id"]),
                title=session.get("title"),
                brand_name=session.get("brand_name"),
                brief=session.get("brief"),
                category=session.get("category"),
                current_state=session.get("current_state", "STATE_GREETING"),
                messages=messages,
                created_at=session.get("created_at", ""),
                updated_at=session.get("updated_at", ""),
            ),
            message="Chat session retrieved successfully",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Failed to get chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat session: {str(e)}",
        )


@router.post(
    "/sessions/{session_id}/resume",
    response_model=SuccessResponse[ChatSessionDetailResponse],
    summary="Resume a past chat session",
)
async def resume_chat_session(
    session_id: str,
    user_id: str = Depends(require_auth),
) -> SuccessResponse[ChatSessionDetailResponse]:
    """Resume a past chat session.

    This endpoint:
    1. Retrieves the session and all messages from the database
    2. Restores the in-memory session state so the behavioral engine can continue
    3. Returns the full session for the client to display

    After calling this endpoint, the client can continue the conversation
    by sending messages to /chat with the same session_id.
    """
    try:
        # Validate UUID format
        UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    try:
        from app.services.chat_persistence import restore_session_from_db
        
        session = await restore_session_from_db(session_id, user_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )
        
        messages = [
            ChatMessageResponse(
                id=str(m["id"]),
                role=m["role"],
                content=m["content"],
                state_before=m.get("state_before"),
                state_after=m.get("state_after"),
                created_at=m.get("created_at", ""),
            )
            for m in session.get("messages", [])
        ]
        
        app_logger.info(f"Resumed chat session {session_id} for user {user_id}")
        
        return success_response(
            data=ChatSessionDetailResponse(
                id=str(session["id"]),
                title=session.get("title"),
                brand_name=session.get("brand_name"),
                brief=session.get("brief"),
                category=session.get("category"),
                current_state=session.get("current_state", "STATE_GREETING"),
                messages=messages,
                created_at=session.get("created_at", ""),
                updated_at=session.get("updated_at", ""),
            ),
            message="Chat session resumed successfully. Continue by sending messages to /chat with this session_id.",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Failed to resume chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume chat session: {str(e)}",
        )


@router.delete(
    "/sessions/{session_id}",
    response_model=SuccessResponse[dict],
    summary="Delete a chat session",
)
async def delete_chat_session_endpoint(
    session_id: str,
    user_id: str = Depends(require_auth),
) -> SuccessResponse[dict]:
    """Delete a chat session and all its messages.

    This permanently removes the conversation history.
    """
    try:
        # Validate UUID format
        UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    try:
        from app.services.chat_persistence import delete_chat_session
        
        deleted = await delete_chat_session(session_id, user_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )
        
        return success_response(
            data={"deleted": True, "session_id": session_id},
            message="Chat session deleted successfully",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Failed to delete chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat session: {str(e)}",
        )
