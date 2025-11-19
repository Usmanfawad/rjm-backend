"""RJM / MIRA RAG pipeline using OpenAI and Pinecone."""

from __future__ import annotations

from typing import List

from app.config.logger import app_logger
from app.config.settings import settings
from app.api.rjm.schemas import (
    GenerateProgramRequest,
    ProgramJSON,
    Persona,
)
from app.services.rjm_vector_store import (
    PINECONE_NAMESPACE,
    describe_index_stats,
    embed_texts,
    get_openai_client,
    get_pinecone_index,
)
from app.services.rjm_canon import (
    get_canon_persona_names,
    get_canon_persona_map,
    get_canon_persona_prompt_list,
    get_generational_by_phylum,
    get_local_culture_personas,
)


# Canonical Activation Plan language from Packaging Logic MASTER 10.22.25
ACTIVATION_PLAN_CANON: list[str] = [
    "Set up campaign as a direct package or PMP package.",
    "Apply segments together for campaign setup using OR methodology within a unified program framework.",
    "Segments are designed to deliver full, high-scale cultural coverage aligned to the brand’s objectives.",
    "Delivery across CTV, streaming video, display, mobile, audio, and social via direct IO and programmatic execution.",
]


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

    query_text = (
        f"Brand: {request.brand_name}\n"
        f"Category: {request.category}\n"
        f"Brief: {request.brief}\n"
        f"Filters: local_culture={request.filters.local_culture}, "
        f"generational={request.filters.generational}, "
        f"multicultural={request.filters.multicultural}"
    )

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


def generate_program_with_rag(request: GenerateProgramRequest) -> ProgramJSON:
    """Run RAG + OpenAI to generate an RJM-style persona program."""
    client = get_openai_client()

    try:
        context = _build_rjm_context(request)
    except RuntimeError as exc:
        app_logger.error(exc)
        raise

    canon_prompt_list = get_canon_persona_prompt_list()
    canon_preview = ", ".join(canon_prompt_list)

    system_prompt = (
        "You are MIRA, the RJM reasoning engine. "
        "You read RJM Packaging Logic, Phylum Index, Narrative Library, and API schemas. "
        "Given a brand brief, you must return a single RJM Persona Program as strict JSON. "
        "Follow Packaging Logic MASTER section order and constraints.\n\n"
        "Output JSON MUST match exactly this schema (omit comments):\n"
        "{\n"
        '  "header": "Brand | Persona Framework",\n'
        '  "key_identifiers": ["string", ... 3-6 items],\n'
        '  "personas": [\n'
        '    {"name": "string", "category": "string", "phylum": "string"}\n'
        '    // 6-20 persona objects\n'
        "  ],\n"
        '  "persona_insights": ["string", ... up to 3 items],\n'
        '  "demos": {"core": "string", "secondary": "string"},\n'
        '  "activation_plan": ["string", ... 3-5 items]\n'
        "}\n\n"
        "Example output (truncated, for format only):\n"
        "{\n"
        '  "header": "Example Brand | Persona Framework",\n'
        '  "key_identifiers": ["Family & Celebration", "Neighborhood Rituals", "..."],\n'
        '  "personas": [\n'
        '    {"name": "Breakfast Burrito", "category": "QSR", "phylum": "Food & Culinary"},\n'
        '    {"name": "Hometown Hero", "category": "Finance & Insurance", "phylum": "Community & Local Pride"},\n'
        "    ...\n"
        "  ],\n"
        '  "persona_insights": ["Breakfast Burrito: ...", "..."],\n'
        '  "demos": {"core": "Adults 25-54", "secondary": "Adults 18+"},\n'
        '  "activation_plan": ["Set up campaign as ...", "..."]\n'
        "}\n\n"
        "Do not include extra keys or text outside the JSON. personas must be 6–20 items.\n\n"
        "Valid phylum values MUST be chosen from this set only (exact strings):\n"
        "['Sports & Competition', 'Gaming & Interactive', 'Food & Culinary', 'Wellness & Body Culture', "
        "'Style & Fashion', 'Luxury & Affluence', 'Work & Hustle', 'Creative & Arts', 'Music & Nightlife', "
        "'Travel & Exploration', 'Tech & Innovation', 'Family & Caregiving', 'Community & Local Pride', "
        "'Pop Culture & Media Junkies', 'Automotive & Car Culture', 'Civic & Politics', 'Education & Growth', "
        "'Shopper Mindset', 'Spiritual & Philosophical', 'Outdoors & Nature', 'Pets & Companionship', "
        "'Moments & Holidays'].\n"
        "The demos.core and demos.secondary values MUST be demographic age strings like "
        "'Adults 25-54' or 'Adults 18+' and MUST NOT be phrases like 'Families with children' or 'Gen Z fans'.\n\n"
        "All persona names in the personas array MUST be chosen ONLY from this allowed canon list "
        "(case-sensitive, no invented names), and each persona must use its exact phylum shown here:\n"
        f"{canon_preview}"
    )

    user_prompt_parts: List[str] = []
    user_prompt_parts.append("RJM CONTEXT (retrieved snippets):")
    user_prompt_parts.append(context or "[no context available]")
    user_prompt_parts.append("\n---\n")
    user_prompt_parts.append("BRAND REQUEST:")
    user_prompt_parts.append(f"Brand: {request.brand_name}")
    user_prompt_parts.append(f"Category: {request.category}")
    user_prompt_parts.append(f"Brief: {request.brief}")
    user_prompt_parts.append(
        f"Filters: local_culture={request.filters.local_culture}, "
        f"generational={request.filters.generational}, "
        f"multicultural={request.filters.multicultural}"
    )
    user_prompt_parts.append(
        f"Personas requested (approximate): {request.personas_requested}"
    )
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
        # If the model did not return valid JSON, fall back to a minimal stub
        app_logger.error("OpenAI response was not valid JSON")
        raise RuntimeError("OpenAI response was not valid JSON; please retry generation.")

    header = raw.get("header") or f"{request.brand_name} | Persona Framework"
    key_identifiers = raw.get("key_identifiers") or []
    personas_raw = raw.get("personas") or []
    persona_insights_raw = raw.get("persona_insights") or []
    demos = raw.get("demos") or {}
    # Always enforce canonical Activation Plan language regardless of model output
    activation_plan = ACTIVATION_PLAN_CANON

    canon_map = get_canon_persona_map()
    raw_personas: List[Persona] = []
    seen_names: set[str] = set()
    for p in personas_raw:
        name = p.get("name")
        if not name:
            continue
        if name not in canon_map:
            # Skip invented or non-canon personas
            continue
        if name in seen_names:
            # Enforce no duplicates within a program
            continue
        seen_names.add(name)
        raw_personas.append(
            Persona(
                name=name,
                category=p.get("category") or request.category,
                phylum=canon_map.get(name),
            )
        )

    # Determine target total personas based on request (respect 6–20 band)
    target_total = max(6, min(request.personas_requested, 20))

    if len(raw_personas) < 6:
        app_logger.error(
            f"Model returned only {len(raw_personas)} valid canon personas after filtering; expected at least 6",
            len(raw_personas),
        )
        raise RuntimeError("Insufficient valid canon personas returned; please retry generation.")

    # Plan reserved slots for generational + local modules.
    # Always try to keep at least 1 slot for local culture if requested.
    desired_gen = 2 if request.filters.generational else 0
    desired_local = 2 if request.filters.local_culture else 0
    max_reserved = max(0, target_total - 6)  # always ensure at least 6 core personas

    # Guarantee at least one local slot if local_culture is requested and we have capacity
    reserved_local = 1 if request.filters.local_culture and max_reserved > 0 else 0
    remaining_reserved_budget = max_reserved - reserved_local
    reserved_gen = min(desired_gen, max(0, remaining_reserved_budget))
    reserved = reserved_local + reserved_gen

    core_limit = min(len(raw_personas), max(6, target_total - reserved))
    personas: List[Persona] = raw_personas[:core_limit]
    seen_names = {p.name for p in personas}

    # Add generational modules if requested and capacity allows,
    # but never consume the reserved_local slot.
    remaining_slots = target_total - len(personas)
    if remaining_slots > 0 and request.filters.generational:
        gen_by_phylum = get_generational_by_phylum()
        used_phyla = {p.phylum for p in personas if p.phylum}
        added = 0
        # Reserve at least one slot for local culture if requested
        gen_slots = remaining_slots - (1 if request.filters.local_culture and remaining_slots > 0 else 0)
        if gen_slots < 0:
            gen_slots = 0
        for phylum in sorted(used_phyla):
            if added >= remaining_slots:
                break
            gen_names = gen_by_phylum.get(phylum) or []
            for gen_name in gen_names:
                if gen_name in seen_names:
                    continue
                if added >= gen_slots:
                    break
                personas.append(
                    Persona(
                        name=gen_name,
                        # Generational modules inherit the brand's ad category
                        category=request.category,
                        phylum=phylum,
                    )
                )
                seen_names.add(gen_name)
                added += 1
                break  # one generational per phylum, then move on
        remaining_slots = target_total - len(personas)

    # Add local culture modules if requested and capacity allows
    if remaining_slots > 0 and request.filters.local_culture:
        local_personas = get_local_culture_personas()
        added = 0
        for name in local_personas:
            if added >= remaining_slots:
                break
            if name in seen_names:
                continue
            personas.append(
                Persona(
                    name=name,
                    # Local culture modules also inherit the brand's ad category
                    category=request.category,
                    phylum="Community & Local Pride",
                )
            )
            seen_names.add(name)
            added += 1
        remaining_slots = target_total - len(personas)

    # Filter persona_insights to only those that reference personas present in the package
    valid_persona_names = {p.name for p in personas}
    persona_insights: List[str] = []
    for insight in persona_insights_raw:
        # Expect pattern like "PersonaName: some text"
        prefix, _, _ = insight.partition(":")
        persona_name = prefix.strip()
        if persona_name in valid_persona_names:
            persona_insights.append(insight)
        # Stop at 3 to respect schema max
        if len(persona_insights) >= 3:
            break

    # If model returned no usable persona insights, synthesize 1–2 simple, canon-safe insights
    if not persona_insights and personas:
        # Use up to 2 core personas for synthesized insights
        for p in personas[:2]:
            persona_insights.append(
                f"{p.name}: Key segment within {p.phylum} supporting {request.category} "
                f"programs built around {', '.join(key_identifiers[:1]).lower() if key_identifiers else 'the brand’s objectives'}."
            )
            if len(persona_insights) >= 2:
                break

    # Normalize demos to RJM-style age ranges, regardless of model wording
    def _normalize_demo(value: object, fallback: str) -> str:
        if not isinstance(value, str):
            return fallback
        v = value.strip()
        # Accept simple patterns starting with 'Adults' and containing a digit
        if v.startswith("Adults") and any(ch.isdigit() for ch in v):
            return v
        return fallback

    default_core_demo = "Adults 25-54"
    default_secondary_demo = "Adults 18+"
    demos = {
        "core": _normalize_demo(demos.get("core"), default_core_demo),
        "secondary": _normalize_demo(demos.get("secondary"), default_secondary_demo),
    }

    return ProgramJSON(
        header=header,
        key_identifiers=list(key_identifiers),
        personas=personas,
        persona_insights=list(persona_insights),
        demos={
            "core": demos.get("core"),
            "secondary": demos.get("secondary"),
        },
        activation_plan=list(activation_plan),
    )



