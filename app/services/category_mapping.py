"""
Advertising category mapping, anchors, and helper utilities for persona selection.

This module re-exports from rjm_ingredient_canon.py for backward compatibility.
All canonical data now lives in rjm_ingredient_canon.py (RJM INGREDIENT CANON 11.26.25).
"""

from __future__ import annotations

# Re-export everything from the new ingredient canon for backward compatibility
from app.services.rjm_ingredient_canon import (
    # Category → Persona Map
    CATEGORY_PERSONA_MAP,
    get_category_personas,
    infer_category,
    CATEGORY_KEYWORDS,
    # Phylum Index
    PHYLUM_PERSONA_MAP,
    PERSONA_TO_PHYLUM,
    get_persona_phylum,
    is_canon_persona,
    get_canonical_name,
    check_phylum_diversity,
    # Ad-Category Anchors
    AD_CATEGORY_ANCHORS,
    ALL_ANCHORS,
    get_category_anchors,
    get_dual_anchors,
    get_brand_categories,
    DUAL_ANCHOR_BRANDS,
    # Generations
    GENERATIONS,
    GENERATIONS_BY_COHORT,
    ALL_GENERATIONAL_NAMES,
    get_generational_segment,
    get_generational_description,
    # Multicultural Expressions
    MULTICULTURAL_EXPRESSIONS,
    MULTICULTURAL_BY_LINEAGE,
    get_multicultural_expressions,
    get_multicultural_description,
    detect_multicultural_lineage,
    MULTICULTURAL_KEYWORDS,
    # Local Culture
    LOCAL_CULTURE_DMAS,
    LOCAL_CULTURE_SET,
    is_local_brief,
    get_local_culture_segment,
    # Rotation Logic
    register_personas_for_rotation,
    register_generational_for_rotation,
    is_persona_recent,
    is_generational_recent,
    clear_rotation_cache,
)

# Legacy aliases for backward compatibility
CATEGORY_PERSONAS = CATEGORY_PERSONA_MAP
CATEGORY_ANCHORS = AD_CATEGORY_ANCHORS
