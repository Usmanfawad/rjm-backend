"""RJM / MIRA RAG pipeline using OpenAI and Pinecone."""

from __future__ import annotations

from typing import List

from app.config.logger import app_logger
from app.config.settings import settings
from app.api.rjm.schemas import GenerateProgramRequest, ProgramJSON, Persona, GenerationalSegment
from app.services.rjm_ingredient_canon import (
    GENERATIONS_BY_COHORT,
    ALL_GENERATIONAL_NAMES,
    ALL_ANCHORS,
    get_category_personas,
    get_dual_anchors,
    get_generational_description,
    infer_category as infer_ad_category,
    is_canon_persona,
    get_persona_phylum,
    get_canonical_name,
    normalize_generational_name,
)
from app.services.rjm_vector_store import (
    PINECONE_NAMESPACE,
    describe_index_stats,
    embed_texts,
    get_openai_client,
    get_pinecone_index,
)
from app.services.rjm_canon import (
    get_canon_persona_prompt_list,
)


# Canonical Activation Plan language from Packaging Logic MASTER 10.22.25
ACTIVATION_PLAN_CANON: list[str] = [
    "Set up campaign as a direct package or PMP package.",
    "Apply segments together for campaign setup using OR methodology within a unified program framework.",
    "Segments are designed to deliver full, high-scale cultural coverage aligned to the brand's objectives.",
    "Delivery across CTV, streaming video, display, mobile, audio, and social via direct IO and programmatic execution.",
]


def _build_system_prompt(
    canon_preview: str,
    inferred_category: str,
    category_personas: List[str],
    category_anchors: List[str],
    generational_options: str,
) -> str:
    # Get first 20 personas from category for explicit guidance
    category_persona_list = category_personas[:20] if category_personas else []
    category_persona_text = ", ".join(category_persona_list) if category_persona_list else canon_preview
    category_anchor_text = ", ".join(category_anchors)
    
    # Create explicit example personas from the category - show structure but indicate LLM should generate unique highlights
    example_personas = category_persona_list[:3] if len(category_persona_list) >= 3 else category_persona_list
    example_json = ",\n    ".join([
        f'{{"name": "{p}", "category": "{inferred_category}", "phylum": "relevant phylum", "highlight": "GENERATE A UNIQUE 7-12 WORD LINE SPECIFIC TO THIS PERSONA AND BRAND"}}'
        for p in example_personas
    ])
    
    return f"""You are MIRA, the RJM reasoning engine.
You read Packaging Logic MASTER 10.22.25, the MIRA Packaging Implementation Spec 11.21.25,
RJM Ingredient Canon 11.26.25, and the Phylum Index MASTER.
Given only a brand name and brief, you must return ONE RJM Persona Program as strict JSON.

Detected advertising category: {inferred_category}

CRITICAL: You MUST return EXACTLY 15 personas in the "personas" array. Not 3, not 4, not 5 — FIFTEEN (15) personas.

Category-first selector — SELECT 15 PERSONAS FROM THIS LIST:
{category_persona_text}

Category anchors (DO NOT include in personas array — these are added separately): {category_anchor_text}

Generational segments (pick 4 total, one from each cohort — DO NOT include in personas array):
{generational_options}

OUTPUT SCHEMA (JSON only):
{{
  "header": "Brand | Persona Framework",
  "advertising_category": "{inferred_category}",
  "key_identifiers": ["string", "string", "string", "string"],
  "personas": [
    {example_json},
    ... CONTINUE UNTIL YOU HAVE EXACTLY 15 PERSONAS ...
  ],
  "generational_segments": [
    {{"name": "Gen Z–...", "highlight": "7-12 word strategist line for this generation"}},
    {{"name": "Millennial–...", "highlight": "7-12 word strategist line"}},
    {{"name": "Gen X–...", "highlight": "7-12 word strategist line"}},
    {{"name": "Boomer–...", "highlight": "7-12 word strategist line"}}
  ],
  "persona_insights": ["string", "string"],
  "demos": {{"core": "string", "secondary": "string", "broad_demo": "optional string"}},
  "activation_plan": [
    "Set up campaign as a direct package or PMP package.",
    "Apply segments together for campaign setup using OR methodology within a unified program framework.",
    "Segments are designed to deliver full, high-scale cultural coverage aligned to the brand's objectives.",
    "Delivery across CTV, streaming video, display, mobile, audio, and social via direct IO and programmatic execution."
  ]
}}

STRICT RULES:
- PERSONAS ARRAY MUST CONTAIN EXACTLY 15 ENTRIES. This is mandatory. Count them.
- Only the first 3-4 personas should have "highlight" values; the rest MUST have "highlight": null.
- HIGHLIGHT FORMAT: The "highlight" field should contain ONLY the description (7-12 words), NOT the persona name.
  CRITICAL: Generate UNIQUE highlights specific to each persona AND the brand/category context. Do NOT reuse generic phrases across different personas or categories.
  Good examples by category:
  - Auto persona: "Thrives on open roads and spontaneous family adventures."
  - Finance persona: "Builds wealth through disciplined planning and smart decisions."
  - QSR persona: "Builds mealtime around pickup, drive-thru, and mobile order."
  - Retail persona: "Hunts for deals that stretch the family budget further."
- Key Identifiers: exactly 4–5 bullets, 7–12 words, strategist tone. DO NOT end with periods — these flow into a sentence.
- Persona Insights: exactly 2 bullets. Percentages must be ONE high band (33–42%) and ONE low band (21–32%) with ≥5 points separation. Rationale describes behavior/mindset; persona nickname appears only at the end in quotes.
  Example: "35% who connect with weekend adventure and shared travel are \"Tailgater.\""
- Demos: Always include Core and Secondary lines using RJM age-range format (e.g., "Adults 25–54"). Add Broad line when reach expansion is needed.
- Generational Segments: Pick exactly 4 from the provided options (one per cohort: Gen Z, Millennial, Gen X, Boomer). Each must have a "highlight" (7-12 words, description only, no name prefix).
- Activation Plan: Use the canonical 4 bullets verbatim.
- No invented persona names — only use names from the category list above.
- Do NOT include anchors or generational segments in the personas array.

Return ONLY the JSON above—no commentary, no Markdown."""


def _ensure_index_ready() -> None:
    """Ensure the Pinecone index already contains data."""
    try:
        stats = describe_index_stats()
    except Exception as exc:  # pragma: no cover - network errors
        raise RuntimeError(f"Pinecone index not available: {exc}") from exc

    namespaces = stats.get("namespaces") or {}
    namespace_stats = namespaces.get(PINECONE_NAMESPACE)
    total_vectors = (
        namespace_stats.get("vector_count", 0)
        if namespace_stats
        else stats.get("total_vector_count", 0)
    )

    if total_vectors == 0:
        raise RuntimeError(
            "Pinecone index is empty. Run /v1/rjm/sync before generating persona programs."
        )


def _build_rjm_context(request: GenerateProgramRequest, top_k: int = 12) -> str:
    """Retrieve top-k relevant RJM chunks for the given request and build a context string."""
    _ensure_index_ready()
    index = get_pinecone_index()

    # Only brand and brief are user inputs; MIRA infers category and modules internally.
    query_text = f"Brand: {request.brand_name}\nBrief: {request.brief}\n"

    query_embedding = embed_texts([query_text])[0]

    result = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        namespace=PINECONE_NAMESPACE,
    )

    contexts: List[str] = []
    for match in result.get("matches", []):
        meta = match.get("metadata") or {}
        text = meta.get("text")
        if text:
            contexts.append(text)

    if not contexts:
        return ""

    return "\n\n⸻\n\n".join(contexts)


def _build_generational_options() -> str:
    """Build a formatted string of available generational segments by cohort."""
    lines = []
    for cohort, segments in GENERATIONS_BY_COHORT.items():
        lines.append(f"{cohort}: {', '.join(segments)}")
    return "\n".join(lines)


def generate_program_with_rag(request: GenerateProgramRequest) -> ProgramJSON:
    """Run RAG + OpenAI to generate an RJM-style persona program.
    
    The LLM handles all creative decisions:
    - Persona selection and phylum diversity
    - Generational segment selection
    - Persona insights with percentages
    - Key identifiers and highlights
    
    We only backfill if the LLM doesn't return enough content.
    """
    client = get_openai_client()

    try:
        context = _build_rjm_context(request)
    except RuntimeError as exc:
        app_logger.error(exc)
        raise

    canon_prompt_list = get_canon_persona_prompt_list()
    canon_preview = ", ".join(canon_prompt_list)

    # Infer advertising category from brand + brief for category-first selection
    category_context_text = f"{request.brand_name} {request.brief}"
    inferred_category = infer_ad_category(category_context_text)
    category_personas = get_category_personas(inferred_category)
    
    # Use dual anchors for brands that span multiple categories (e.g., L'Oréal)
    category_anchors = get_dual_anchors(request.brand_name, inferred_category)

    generational_options = _build_generational_options()

    system_prompt = _build_system_prompt(
        canon_preview=canon_preview,
        inferred_category=inferred_category,
        category_personas=category_personas,
        category_anchors=category_anchors,
        generational_options=generational_options,
    )

    user_prompt_parts: List[str] = []
    user_prompt_parts.append("RJM CONTEXT (retrieved snippets):")
    user_prompt_parts.append(context or "[no context available]")
    user_prompt_parts.append("\n---\n")
    user_prompt_parts.append(
        "BRAND REQUEST (only brand and brief are provided; infer category, phyla, and modules internally):"
    )
    user_prompt_parts.append(f"Brand: {request.brand_name}")
    user_prompt_parts.append(f"Brief: {request.brief}")
    user_prompt_parts.append(f"Detected category (primary selector): {inferred_category}")
    if category_personas:
        preview = ", ".join(category_personas[:60])
        user_prompt_parts.append(f"Category personas to prioritize: {preview}")
    user_prompt_parts.append(f"Category anchors for portfolio placement: {', '.join(category_anchors)}")
    user_prompt = "\n".join(user_prompt_parts)

    completion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = completion.choices[0].message.content or ""

    import json

    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        app_logger.error("OpenAI response was not valid JSON")
        raise RuntimeError("OpenAI response was not valid JSON; please retry generation.")

    header = raw.get("header") or f"{request.brand_name} | Persona Framework"
    key_identifiers = raw.get("key_identifiers") or []
    personas_raw = raw.get("personas") or []
    advertising_category = raw.get("advertising_category") or inferred_category
    demos = raw.get("demos") or {}
    generational_segments_raw = raw.get("generational_segments") or []
    persona_insights_raw = raw.get("persona_insights") or []
    
    # Always enforce canonical Activation Plan language regardless of model output
    activation_plan = ACTIVATION_PLAN_CANON

    # Validate personas against canon (filter out invented names, but trust LLM's selection)
    valid_personas: List[Persona] = []
    seen_names: set[str] = set()
    
    # Build set of anchor names to skip (LLM sometimes puts anchors in personas array)
    anchor_names = set(ALL_ANCHORS)
    
    app_logger.info(f"Processing {len(personas_raw)} personas from LLM response")
    
    for p in personas_raw:
        name = p.get("name")
        if not name:
            continue
        
        # Skip anchors that LLM mistakenly put in personas array
        if name in anchor_names or name.startswith("RJM "):
            app_logger.debug(f"Skipping anchor in personas array: {name}")
            continue
        
        # Skip generational segments in the core persona list
        if name in ALL_GENERATIONAL_NAMES:
            app_logger.debug(f"Skipping generational segment in personas array: {name}")
            continue
        
        # Get canonical name (handles variations like "Budget-Minded" vs "Budget Minded")
        canonical_name = get_canonical_name(name)
        
        if not is_canon_persona(canonical_name):
            # Log but don't skip - try the original name too
            app_logger.warning(f"Persona '{name}' not found in canon (canonical: '{canonical_name}')")
            # Try the original name as-is
            if is_canon_persona(name):
                canonical_name = name
            else:
                continue
        
        if canonical_name in seen_names:
            continue
        
        seen_names.add(canonical_name)
        valid_personas.append(
            Persona(
                name=canonical_name,
                category=p.get("category"),
                phylum=get_persona_phylum(canonical_name),
                highlight=p.get("highlight"),
            )
        )
    
    app_logger.info(f"Validated {len(valid_personas)} personas from LLM response")

    # Validate generational segments (trust LLM's selection, just validate they exist)
    # Handle both old format (list of strings) and new format (list of objects with name/highlight)
    valid_generational: List[dict] = []
    seen_gen_names: set[str] = set()
    for seg in generational_segments_raw:
        if isinstance(seg, dict):
            name = seg.get("name", "")
            highlight = seg.get("highlight", "")
        else:
            name = seg
            highlight = ""
        
        # Normalize the generational name (handles "Gen-Z Prompted" -> "Gen Z–Prompted")
        canonical_gen_name = normalize_generational_name(name)
        if canonical_gen_name and canonical_gen_name not in seen_gen_names:
            seen_gen_names.add(canonical_gen_name)
            valid_generational.append({"name": canonical_gen_name, "highlight": highlight})
        elif name and not canonical_gen_name:
            app_logger.warning(f"Skipping unrecognized generational segment: {name}")
    
    # BACKFILL ONLY: If LLM didn't return enough generational segments
    if len(valid_generational) < 4:
        app_logger.info(f"Backfilling generational segments (LLM returned {len(valid_generational)})")
        for cohort, segments in GENERATIONS_BY_COHORT.items():
            if len(valid_generational) >= 4:
                break
            has_cohort = any(g["name"].startswith(cohort) for g in valid_generational)
            if not has_cohort and segments:
                valid_generational.append({"name": segments[0], "highlight": ""})
    
    # BACKFILL: If any generational segment has empty highlight, create one from description
    for seg in valid_generational:
        if not seg.get("highlight"):
            desc = get_generational_description(seg["name"])
            if desc:
                # Extract a short highlight from the description (first ~10 words after "Curated for")
                if "—" in desc:
                    short_desc = desc.split("—")[1].strip()[:80]
                else:
                    short_desc = desc.replace("Curated for a generation that ", "").strip()[:80]
                # Truncate to ~10 words
                words = short_desc.split()[:10]
                seg["highlight"] = " ".join(words).rstrip(".,;—") + "."

    # BACKFILL ONLY: If LLM didn't return enough personas, add from category pool
    if len(valid_personas) < 6:
        app_logger.warning(
            f"Model returned only {len(valid_personas)} valid canon personas; backfilling from category pool"
        )
        # Get personas from the detected category to backfill
        for persona_name in category_personas:
            if len(valid_personas) >= 15:
                break
            if persona_name in seen_names:
                continue
            if persona_name in ALL_GENERATIONAL_NAMES:
                continue
            if is_canon_persona(persona_name):
                seen_names.add(persona_name)
                valid_personas.append(
                    Persona(
                        name=persona_name,
                        category=inferred_category,
                        phylum=get_persona_phylum(persona_name),
                        highlight=None,
                    )
                )
        app_logger.info(f"After backfill: {len(valid_personas)} personas")

    # Use LLM's persona insights directly (trust the LLM's percentages and content)
    persona_insights = persona_insights_raw[:2] if persona_insights_raw else []
    
    # BACKFILL ONLY: If LLM didn't return insights
    if len(persona_insights) < 2:
        app_logger.info("Backfilling persona insights (LLM returned insufficient)")
        # Create simple fallback insights using available personas
        fallback_personas = [p.name for p in valid_personas[:2]] or ["Luxury Insider", "Self Love"]
        while len(persona_insights) < 2:
            idx = len(persona_insights)
            persona_insights.append(
                f"Audiences who connect with this brand's cultural positioning are \"{fallback_personas[idx % len(fallback_personas)]}.\""
            )

    # Normalize demos (accept LLM's values, only provide fallbacks if missing)
    def _normalize_demo(value: object, fallback: str) -> str:
        if not isinstance(value, str) or not value.strip():
            return fallback
        return value.strip()

    default_core_demo = "Adults 25-54"
    default_secondary_demo = "Adults 18+"
    default_broad_demo = "Adults 18-64"
    normalized_demos = {
        "core": _normalize_demo(demos.get("core"), default_core_demo),
        "secondary": _normalize_demo(demos.get("secondary"), default_secondary_demo),
        "broad_demo": _normalize_demo(demos.get("broad_demo"), default_broad_demo),
    }

    # Convert generational dicts to GenerationalSegment objects
    generational_segment_objects = [
        GenerationalSegment(name=g["name"], highlight=g.get("highlight"))
        for g in valid_generational[:4]
    ]

    return ProgramJSON(
        header=header,
        advertising_category=advertising_category,
        key_identifiers=list(key_identifiers),
        personas=valid_personas,
        generational_segments=generational_segment_objects,
        persona_insights=list(persona_insights),
        demos=normalized_demos,
        activation_plan=list(activation_plan),
    )
