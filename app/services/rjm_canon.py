"""
Utilities for loading RJM canon persona names from the ingredient canon.

This module now primarily wraps rjm_ingredient_canon.py (RJM INGREDIENT CANON 11.26.25).
Legacy file-based loading is retained as fallback for backward compatibility.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Set

from app.config.logger import app_logger
from app.config.settings import settings
from app.services.rjm_ingredient_canon import (
    PERSONA_TO_PHYLUM,
    PHYLUM_PERSONA_MAP,
    GENERATIONS,
    GENERATIONS_BY_COHORT,
    ALL_GENERATIONAL_NAMES,
    LOCAL_CULTURE_DMAS,
)


def _safe_read(path: Path) -> List[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    return text.splitlines()


@lru_cache(maxsize=1)
def get_canon_persona_map() -> Dict[str, str]:
    """Return mapping of persona_name -> phylum from RJM Ingredient Canon."""
    app_logger.info(f"Loaded {len(PERSONA_TO_PHYLUM)} canon personas with phylum mapping from Ingredient Canon")
    return PERSONA_TO_PHYLUM


@lru_cache(maxsize=1)
def get_canon_persona_names() -> List[str]:
    """Return a sorted list of canon persona names for prompting."""
    names = sorted(PERSONA_TO_PHYLUM.keys())
    app_logger.info(f"Loaded {len(names)} canon persona names for prompting")
    return names


@lru_cache(maxsize=1)
def get_canon_persona_prompt_list() -> List[str]:
    """Return persona names annotated with their phylum for prompt conditioning."""
    return [f"{name} ({phylum})" for name, phylum in sorted(PERSONA_TO_PHYLUM.items())]


@lru_cache(maxsize=1)
def get_generational_by_phylum() -> Dict[str, List[str]]:
    """
    Return generational segments organized by cohort.
    
    Note: In the new Ingredient Canon, generations are organized by cohort (Gen Z, Millennial, etc.)
    rather than by persona phylum. This function now returns cohort-based grouping.
    """
    app_logger.info(f"Loaded generational anchors for {len(GENERATIONS_BY_COHORT)} cohorts")
    return GENERATIONS_BY_COHORT


@lru_cache(maxsize=1)
def get_all_generational_names() -> Set[str]:
    """Return all generational segment names."""
    return ALL_GENERATIONAL_NAMES


@lru_cache(maxsize=1)
def get_generational_descriptions() -> Dict[str, str]:
    """Return generational segment names with their descriptions."""
    return GENERATIONS


@lru_cache(maxsize=1)
def get_local_culture_personas() -> List[str]:
    """Return Local Culture DMA segment names."""
    app_logger.info(f"Loaded {len(LOCAL_CULTURE_DMAS)} local culture DMA segments")
    return LOCAL_CULTURE_DMAS


@lru_cache(maxsize=1)
def get_phylum_persona_map() -> Dict[str, List[str]]:
    """Return phylum -> list of personas mapping."""
    return PHYLUM_PERSONA_MAP
