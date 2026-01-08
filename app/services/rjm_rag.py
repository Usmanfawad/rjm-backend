"""RJM / MIRA RAG pipeline using OpenAI and Pinecone."""

from __future__ import annotations

import re
from typing import List

from app.config.logger import app_logger
from app.config.settings import settings
from app.api.rjm.schemas import GenerateProgramRequest, ProgramJSON, Persona, GenerationalSegment
from app.services.rjm_ingredient_canon import (
    GENERATIONS_BY_COHORT,
    ALL_GENERATIONAL_NAMES,
    ALL_ANCHORS,
    get_category_personas,
    get_generational_description,
    infer_category_with_llm,  # Use LLM-based category detection
    get_persona_phylum,
    get_canonical_name,
    normalize_generational_name,
    # Overlay detection and retrieval
    detect_multicultural_lineage,
    get_multicultural_expressions,
    is_local_brief,
    get_local_culture_segment,
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

═══════════════════════════════════════════════════════════════════════════════
CRITICAL CATEGORY CONSTRAINT - READ CAREFULLY
═══════════════════════════════════════════════════════════════════════════════

You MUST select personas ONLY from the category-specific pool below.
This is the PRIMARY SELECTOR from RJM Ingredient Canon 11.26.25.

FORBIDDEN: Using personas from other categories. For example:
- "Budget-Minded", "Bargain Hunter", "Savvy Shopper" are CPG/Retail personas - DO NOT use for Luxury & Fashion
- "Luxury Insider", "Glam Life" are Luxury personas - DO NOT use for QSR

ANY PERSONA NOT IN THE LIST BELOW WILL BE REJECTED.

Category-first selector — SELECT EXACTLY 15 PERSONAS FROM THIS LIST ONLY:
{category_persona_text}

═══════════════════════════════════════════════════════════════════════════════

CRITICAL: You MUST return EXACTLY 15 personas in the "personas" array. Not 3, not 4, not 5 — FIFTEEN (15) personas.

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
    
    Uses PersonaAuthority for centralized governance:
    - Category-bounded persona selection
    - Phylum diversity enforcement
    - Highlight/insight separation
    - Rotation for freshness
    
    The LLM handles creative decisions, PersonaAuthority enforces structural rules.
    """
    from app.services.persona_authority import PersonaAuthority
    
    client = get_openai_client()

    try:
        context = _build_rjm_context(request)
    except RuntimeError as exc:
        app_logger.error(exc)
        raise

    canon_prompt_list = get_canon_persona_prompt_list()
    canon_preview = ", ".join(canon_prompt_list)

    # Use LLM to accurately detect advertising category (PRIMARY METHOD)
    # This correctly handles well-known brands like Starbucks, Fendi, Verizon, Peloton
    inferred_category = infer_category_with_llm(request.brand_name, request.brief)
    app_logger.info(f"Category detected for '{request.brand_name}': {inferred_category}")
    category_personas = get_category_personas(inferred_category)
    
    # Create PersonaAuthority for this generation (SINGLE SOURCE OF TRUTH)
    authority = PersonaAuthority(
        category=inferred_category,
        brand_name=request.brand_name,
        brief=request.brief,
    )

    generational_options = _build_generational_options()

    system_prompt = _build_system_prompt(
        canon_preview=canon_preview,
        inferred_category=inferred_category,
        category_personas=category_personas,
        category_anchors=authority.anchors,
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
    user_prompt_parts.append(f"Category anchors for portfolio placement: {', '.join(authority.anchors)}")
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

    # === USE PERSONA AUTHORITY FOR VALIDATION ===
    # Extract persona names from LLM output
    llm_persona_names = []
    llm_persona_highlights = {}  # Map name -> highlight

    for p in personas_raw:
        name = p.get("name")
        if not name:
            continue
        # Skip anchors and generational segments
        if name in ALL_ANCHORS or name.startswith("RJM ") or name in ALL_GENERATIONAL_NAMES:
            continue
        llm_persona_names.append(name)
        if p.get("highlight"):
            llm_persona_highlights[name] = p.get("highlight")
    
    app_logger.info(f"Processing {len(llm_persona_names)} personas from LLM for category: {inferred_category}")

    # Validate personas through PersonaAuthority (enforces category boundaries)
    validated_names = authority.validate_personas(llm_persona_names, log_rejections=True)
    
    # Build Persona objects with validated names
    valid_personas: List[Persona] = []
    seen_names: set[str] = set()
    
    for name in validated_names:
        if name in seen_names:
            continue
        seen_names.add(name)
        
        # Get canonical name for phylum lookup
        canonical = get_canonical_name(name)
        
        # Check if this persona had a highlight from LLM
        highlight = None
        for llm_name, llm_highlight in llm_persona_highlights.items():
            if get_canonical_name(llm_name) == canonical:
                highlight = llm_highlight
                break
        
        valid_personas.append(
            Persona(
                name=canonical,
                category=inferred_category,
                phylum=get_persona_phylum(canonical),
                highlight=highlight,
            )
        )
    
    # Build portfolio through PersonaAuthority (handles diversity, rotation, backfill)
    portfolio_names = authority.build_portfolio([p.name for p in valid_personas], target_count=15)
    
    # Ensure valid_personas includes all portfolio names
    for name in portfolio_names:
        if name not in seen_names:
                seen_names.add(name)
                valid_personas.append(
                    Persona(
                        name=name,
                        category=inferred_category,
                        phylum=get_persona_phylum(name),
                        highlight=None,
                    )
                )
    
    app_logger.info(
        f"PersonaAuthority built portfolio: {len(portfolio_names)} personas, "
        f"diversity stats: {authority.context.get_phylum_distribution()}"
    )

    # === USE PERSONA AUTHORITY FOR GENERATIONAL SEGMENTS ===
    # Extract LLM suggestions for generational segments
    llm_generational_names = []
    llm_generational_highlights = {}
    
    for seg in generational_segments_raw:
        if isinstance(seg, dict):
            name = seg.get("name", "")
            highlight = seg.get("highlight", "")
        else:
            name = seg
            highlight = ""
        
        canonical = normalize_generational_name(name)
        if canonical:
            llm_generational_names.append(canonical)
            if highlight:
                llm_generational_highlights[canonical] = highlight
    
    # Select generational segments through PersonaAuthority
    final_generational_names = authority.select_generational(llm_generational_names)
    
    # Build generational segment dicts with highlights
    valid_generational: List[dict] = []
    for name in final_generational_names:
        highlight = llm_generational_highlights.get(name, "")
        
        # BACKFILL: If no highlight, create from description
        if not highlight:
            desc = get_generational_description(name)
            if desc:
                if "—" in desc:
                    short_desc = desc.split("—")[1].strip()[:80]
                else:
                    short_desc = desc.replace("Curated for a generation that ", "").strip()[:80]
                words = short_desc.split()[:10]
                highlight = " ".join(words).rstrip(".,;—") + "."
        
        valid_generational.append({"name": name, "highlight": highlight})
    
    app_logger.info(f"PersonaAuthority selected generational segments: {final_generational_names}")

    # === USE PERSONA AUTHORITY FOR HIGHLIGHT SELECTION ===
    # Select highlights through PersonaAuthority (ensures freshness, diversity)
    personas_with_highlights = [p.name for p in valid_personas if p.highlight]
    highlight_names = authority.select_highlights(personas_with_highlights, count=3)
    
    # Register highlight names in authority context
    for name in highlight_names:
        authority.context.add_to_highlights(name)

    # === USE PERSONA AUTHORITY FOR INSIGHT VALIDATION ===
    # Select personas for insights (must be different from highlights)
    insight_candidates = [p.name for p in valid_personas if p.name not in highlight_names]
    authority.select_for_insights(insight_candidates, count=2)  # Registers in context
    
    # Validate and fix persona insights
    persona_insights = []
    for insight in persona_insights_raw[:2]:
        is_valid, mentioned_persona, error = authority.validate_insight_text(insight)
        if not is_valid and error:
            # Fix the insight by replacing invalid persona
            fixed_insight = authority.fix_insight_persona(insight)
            persona_insights.append(fixed_insight)
            app_logger.info(f"Fixed insight: {error}")
        else:
            persona_insights.append(insight)
    
    # BACKFILL: If LLM didn't return enough insights
    if len(persona_insights) < 2:
        app_logger.info("Backfilling persona insights (LLM returned insufficient)")
        # Use personas from context that aren't in highlights
        fallback_personas = [
            p.name for p in valid_personas 
            if p.name not in highlight_names
        ][:2] or [valid_personas[0].name if valid_personas else "Self Love"]
        
        while len(persona_insights) < 2:
            idx = len(persona_insights)
            persona_name = fallback_personas[idx % len(fallback_personas)]
            persona_insights.append(
                f"Audiences who connect with this brand's cultural positioning are \"{persona_name}.\""
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

    # ═══════════════════════════════════════════════════════════════════════════
    # CONTEXTUAL OVERLAYS (from Ingredient Canon Section IV)
    # ═══════════════════════════════════════════════════════════════════════════

    # A. Multicultural Expressions - only when brief requires multicultural targeting
    multicultural_overlays: List[str] = []
    detected_lineage = detect_multicultural_lineage(request.brief)
    if detected_lineage:
        multicultural_overlays = get_multicultural_expressions(detected_lineage)[:5]
        app_logger.info(f"Multicultural overlay detected: {detected_lineage} -> {multicultural_overlays}")

    # B. Local Culture Segments - only for geo-targeted campaigns
    local_culture_overlays: List[str] = []
    if is_local_brief(request.brief):
        # Try to extract specific DMA from brief
        # For now, we note it's geo-targeted and the user can specify DMAs later
        app_logger.info("Local/geo-targeted brief detected - Local Culture segments applicable")
        # Extract potential city/region mentions for segment matching
        city_pattern = r'\b(new york|los angeles|chicago|houston|phoenix|philadelphia|san antonio|san diego|dallas|austin|miami|atlanta|seattle|denver|boston|nashville|portland|las vegas|detroit|minneapolis|charlotte)\b'
        matches = re.findall(city_pattern, request.brief.lower())
        for city in matches[:5]:  # Max 5 local segments
            segment = get_local_culture_segment(city)
            if segment and segment not in local_culture_overlays:
                local_culture_overlays.append(segment)
        if local_culture_overlays:
            app_logger.info(f"Local Culture segments added: {local_culture_overlays}")

    return ProgramJSON(
        header=header,
        advertising_category=advertising_category,
        key_identifiers=list(key_identifiers),
        personas=valid_personas,
        generational_segments=generational_segment_objects,
        category_anchors=authority.anchors,  # Use PersonaAuthority for anchors
        multicultural_expressions=multicultural_overlays,
        local_culture_segments=local_culture_overlays,
        persona_insights=list(persona_insights),
        demos=normalized_demos,
        activation_plan=list(activation_plan),
    )
