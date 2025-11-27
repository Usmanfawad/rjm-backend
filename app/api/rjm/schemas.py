"""Request and response schemas for RJM / MIRA persona program generation."""

from typing import Dict, List, Optional

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



