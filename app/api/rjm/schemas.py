"""Request and response schemas for RJM / MIRA persona program generation and chat."""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class GenerateProgramRequest(BaseModel):
    """Request schema for POST /v1/rjm/generate."""

    brief: str = Field(
        ...,
        min_length=1,
        description="Brand brief or intuitive text prompt describing the campaign.",
    )
    brand_name: str = Field(
        ...,
        min_length=1,
        description="Advertiser or client name requesting a persona program.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "brief": "Beauty brand focused on ritual, self-expression, and confidence.",
                "brand_name": "Example Brand",
            }
        }
    }


class Persona(BaseModel):
    """Single RJM persona entry in a program."""

    name: str = Field(..., description="Persona name from the RJM canon.")
    category: Optional[str] = Field(
        default=None, description="Advertising category alignment for this persona."
    )
    phylum: Optional[str] = Field(
        default=None, description="Cultural lane / phylum this persona belongs to."
    )
    highlight: Optional[str] = Field(
        default=None,
        description="7–12 word strategist-style highlight line for this persona.",
    )


class GenerationalSegment(BaseModel):
    """Generational segment with optional highlight."""

    name: str = Field(..., description="Generational segment name (e.g., Gen Z–SelfTok).")
    highlight: Optional[str] = Field(
        default=None,
        description="7–12 word strategist-style highlight line for this generation.",
    )


class ProgramJSON(BaseModel):
    """JSON representation of an RJM persona program."""

    header: str = Field(
        ...,
        description="Program title in the form '[Brand] | Persona Framework'.",
    )
    advertising_category: Optional[str] = Field(
        default=None,
        description="Detected RJM advertising category (e.g., QSR, Retail & E-Commerce).",
    )
    key_identifiers: List[str] = Field(
        ...,
        min_length=3,
        max_length=6,
        description="3–6 macro cultural themes that summarize the program.",
    )
    personas: List[Persona] = Field(
        ...,
        min_length=6,
        max_length=20,
        description="List of core personas included in the program (not including generational segments).",
    )
    generational_segments: List[GenerationalSegment] = Field(
        default_factory=list,
        max_length=4,
        description="4 generational segments (one per cohort: Gen Z, Millennial, Gen X, Boomer) with highlights.",
    )
    category_anchors: List[str] = Field(
        default_factory=list,
        max_length=2,
        description="Ad-category anchor segments (e.g., 'RJM CPG', 'RJM Luxury & Fashion'). Always included.",
    )
    multicultural_expressions: List[str] = Field(
        default_factory=list,
        max_length=5,
        description="Multicultural expression overlays. Only included when brief requires multicultural targeting.",
    )
    local_culture_segments: List[str] = Field(
        default_factory=list,
        max_length=10,
        description="Local culture DMA segments. Only included for geo-targeted campaigns.",
    )
    persona_insights: List[str] = Field(
        default_factory=list,
        description="Up to 3 persona insight bullets.",
    )
    demos: Dict[str, Optional[str]] = Field(
        default_factory=lambda: {"core": None, "secondary": None, "broad_demo": None},
        description="Demo splits (core, secondary, optional broad coverage).",
    )
    activation_plan: List[str] = Field(
        default_factory=list,
        description="3–5 bullets describing how to activate this program in media.",
    )


class GenerateProgramResponse(BaseModel):
    """Response schema for POST /v1/rjm/generate."""

    program_json: ProgramJSON = Field(
        ..., description="Structured persona program following RJM schema."
    )
    program_text: str = Field(
        ...,
        description="Human-readable text block formatted per Packaging Logic MASTER.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "program_json": {
                    "header": "Example QSR | Persona Framework",
                    "advertising_category": "QSR",
                    "key_identifiers": [
                        "Family & Celebration",
                        "Neighborhood Rituals",
                        "Value & Comfort",
                    ],
                    "personas": [
                        {
                            "name": "Breakfast Burrito",
                            "category": "QSR",
                            "phylum": "Food & Culinary",
                        },
                        {
                            "name": "Hometown Hero",
                            "category": "Finance & Insurance",
                            "phylum": "Community & Local Pride",
                        },
                    ],
                    "persona_insights": [
                        "Breakfast Burrito: Early risers who wrap energy and convenience together.",
                        "Hometown Hero: Community champions who stay rooted where they're from.",
                    ],
                    "demos": {
                        "core": "Adults 25–54",
                        "secondary": "Adults 18+",
                        "broad_demo": "Adults 18–64",
                    },
                    "activation_plan": [
                        "Set up campaign as a direct package or PMP package.",
                        "Apply segments together using OR methodology within a unified program framework.",
                        "If ops are constrained, prioritize 4 core personas for execution.",
                    ],
                },
                "program_text": "Example QSR | Persona Framework\nCurated for those who see everyday meals as connection and comfort. Neighborhood stops become small rituals of flavor, family, and familiar faces.\n\n🔑 Key Identifiers\n- Family & Celebration\n- Neighborhood Rituals\n- Value & Comfort\n\n✨ Personas\n- Breakfast Burrito (Food & Culinary)\n- Hometown Hero (Community & Local Pride)\n\n📊 Persona Insights\n- Breakfast Burrito: Early risers who wrap energy and convenience together.\n- Hometown Hero: Community champions who stay rooted where they're from.\n\n👥 Demos\n- Core: Adults 25–54\n- Secondary: Adults 18+\n\nActivation Plan\n- Set up campaign as a direct package or PMP package.\n- Apply segments together using OR methodology within a unified program framework.\n- If ops are constrained, prioritize 4 core personas for execution.\n\n⸻",
            }
        }
    }


class DocumentSyncDetail(BaseModel):
    """Per-document sync result."""

    relative_path: str
    action: str = Field(
        description="created, updated, unchanged, or deleted",
    )
    chunk_count: int = Field(ge=0, description="Number of chunks stored for this document")


class SyncSummary(BaseModel):
    """Aggregate sync summary stats."""

    total_files: int = Field(ge=0)
    created: int = Field(ge=0)
    updated: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    deleted: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)


class SyncResponse(BaseModel):
    """Response payload for /v1/rjm/sync."""

    summary: SyncSummary
    details: List[DocumentSyncDetail] = Field(default_factory=list)


class ChatMessage(BaseModel):
    """Single chat message in a MIRA conversational session."""

    role: Literal["user", "assistant"] = Field(
        ...,
        description="Message role. System behavior is governed by the behavioral engine, not this field.",
    )
    content: str = Field(..., min_length=1, description="Message text content.")


class MiraChatRequest(BaseModel):
    """Request schema for POST /v1/rjm/chat."""

    messages: List[ChatMessage] = Field(
        ...,
        min_length=1,
        description="Full message history for this turn (at minimum, the latest user message).",
    )
    state: Optional[str] = Field(
        default=None,
        description=(
            "Current behavioral state id (e.g., STATE_GREETING, STATE_INPUT). "
            "If omitted, the engine assumes a fresh GREETING entry."
        ),
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Opaque session identifier returned by the server. Send it back each turn for memory.",
    )
    brand_name: Optional[str] = Field(
        default=None,
        description=(
            "Optional explicit brand name. Required once moving into program generation / reasoning."
        ),
    )
    brief: Optional[str] = Field(
        default=None,
        description=(
            "Optional explicit campaign brief. Required once moving into program generation / reasoning."
        ),
    )


class MiraChatResponse(BaseModel):
    """Response schema for a single MIRA chat turn."""

    reply: str = Field(
        ...,
        description="MIRA's strategist-style reply text, with guiding-move behavior applied.",
    )
    state: str = Field(
        ...,
        description="Next behavioral state id that the client should send back on the next turn.",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Opaque session identifier to persist memory server-side.",
    )
    # Optional debug hook to help local development; not for end users.
    debug_state_was: Optional[str] = Field(
        default=None,
        description="Previous state id used to compute this reply (for debugging / logging).",
    )
    # Optional generation data for saving persona programs
    generation_data: Optional[Dict] = Field(
        default=None,
        description="Generated persona program data if a program was generated in this turn.",
    )


class TranscriptionResponse(BaseModel):
    """Response schema for audio transcription."""

    text: str = Field(
        ...,
        description="Transcribed text from the audio input.",
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Duration of the processed audio in seconds.",
    )


class PersonaGenerationResponse(BaseModel):
    """Response schema for a saved persona generation."""

    id: str = Field(..., description="Unique identifier for the generation")
    brand_name: str = Field(..., description="Brand name for the program")
    brief: str = Field(..., description="Campaign brief")
    program_text: str = Field(..., description="Human-readable formatted program text")
    program_json: Optional[Dict] = Field(
        default=None,
        description="Structured program data as JSON"
    )
    advertising_category: Optional[str] = Field(
        default=None,
        description="Detected advertising category"
    )
    source: str = Field(
        default="generator",
        description="Source of generation: 'generator' or 'chat'"
    )
    created_at: str = Field(..., description="ISO timestamp of when the program was generated")


class PersonaGenerationListResponse(BaseModel):
    """Response schema for listing persona generations."""

    generations: List[PersonaGenerationResponse] = Field(
        default_factory=list,
        description="List of persona generations"
    )
    total: int = Field(default=0, description="Total number of generations")


# ============================================
# Chat Session Schemas (for persistence)
# ============================================

class ChatSessionSummary(BaseModel):
    """Summary of a chat session for listing."""

    id: str = Field(..., description="Unique session identifier")
    title: Optional[str] = Field(default=None, description="Session title (auto-generated from first message or brand)")
    brand_name: Optional[str] = Field(default=None, description="Brand name if captured")
    category: Optional[str] = Field(default=None, description="Detected advertising category")
    message_count: int = Field(default=0, description="Number of messages in this session")
    current_state: str = Field(default="STATE_GREETING", description="Current behavioral state")
    created_at: str = Field(..., description="ISO timestamp of session creation")
    updated_at: str = Field(..., description="ISO timestamp of last activity")


class ChatSessionListResponse(BaseModel):
    """Response schema for listing chat sessions."""

    sessions: List[ChatSessionSummary] = Field(
        default_factory=list,
        description="List of chat sessions"
    )
    total: int = Field(default=0, description="Total number of sessions")


class ChatMessageResponse(BaseModel):
    """Response schema for a single chat message."""

    id: str = Field(..., description="Message unique identifier")
    role: Literal["user", "assistant"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    state_before: Optional[str] = Field(default=None, description="Behavioral state before this message")
    state_after: Optional[str] = Field(default=None, description="Behavioral state after this message")
    created_at: str = Field(..., description="ISO timestamp of message creation")


class ChatSessionDetailResponse(BaseModel):
    """Full chat session with all messages for resumption."""

    id: str = Field(..., description="Unique session identifier")
    title: Optional[str] = Field(default=None, description="Session title")
    brand_name: Optional[str] = Field(default=None, description="Brand name if captured")
    brief: Optional[str] = Field(default=None, description="Campaign brief if captured")
    category: Optional[str] = Field(default=None, description="Detected advertising category")
    current_state: str = Field(default="STATE_GREETING", description="Current behavioral state for resumption")
    messages: List[ChatMessageResponse] = Field(
        default_factory=list,
        description="All messages in chronological order"
    )
    created_at: str = Field(..., description="ISO timestamp of session creation")
    updated_at: str = Field(..., description="ISO timestamp of last activity")



