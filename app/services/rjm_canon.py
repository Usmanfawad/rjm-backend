"""Utilities for loading RJM canon persona names from the text corpus."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Set

from app.config.logger import app_logger
from app.config.settings import settings


def _safe_read(path: Path) -> List[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    return text.splitlines()


def _from_narrative_library(base: Path) -> Set[str]:
    """Extract persona names from Narrative Library by header pattern."""
    narrative_path = base / "Narrative Library 10-23-25.txt"
    if not narrative_path.exists():
        app_logger.warning("Narrative Library not found at %s", narrative_path)
        return set()

    lines = _safe_read(narrative_path)
    names: Set[str] = set()
    last_non_empty = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Persona name is the line immediately before "Persona Insights"
        if stripped.startswith("Persona Insights"):
            if last_non_empty and not last_non_empty.startswith("•"):
                names.add(last_non_empty.strip("• ").strip())
        last_non_empty = stripped
    return names


def _from_phylum_index(base: Path) -> Dict[str, str]:
    """Extract persona -> phylum mapping from Phylum Index SECTION I."""
    phylum_path = base / "Phylum Index MASTER 10-22-25.txt"
    if not phylum_path.exists():
        app_logger.warning("Phylum Index not found at %s", phylum_path)
        return set()

    lines = _safe_read(phylum_path)
    persona_to_phylum: Dict[str, str] = {}
    in_persona_section = False
    current_phylum: str | None = None

    for line in lines:
        stripped = line.strip()
        if "SECTION I — PERSONAS PHYLUM MAP" in stripped:
            in_persona_section = True
            continue
        if "SECTION II — AD-CATEGORY ANCHORS PHYLUM MAP" in stripped:
            break
        if not in_persona_section:
            continue
        # Phylum headers look like "Food & Culinary (19)"
        if "(" in stripped and ")" in stripped and "•" not in stripped:
            current_phylum = stripped.split("(")[0].strip()
            continue
        # Skip separators
        if not stripped or stripped.startswith("SECTION") or stripped.startswith("⸻"):
            continue
        # Lines with personas are usually in the form "LeBron • QB • Lasso • ..."
        if "•" in stripped and current_phylum:
            parts = [p.strip() for p in stripped.split("•") if p.strip()]
            for part in parts:
                if "(" in part and ")" in part:
                    continue
                persona_to_phylum[part] = current_phylum
    return persona_to_phylum


@lru_cache(maxsize=1)
def get_canon_persona_map() -> Dict[str, str]:
    """Return mapping of persona_name -> phylum from Official Phylum Index."""
    base = Path(settings.RJM_DOCS_DIR).resolve()
    persona_map = _from_phylum_index(base)
    app_logger.info(f"Loaded {len(persona_map)} canon personas with phylum mapping")
    return persona_map


@lru_cache(maxsize=1)
def get_canon_persona_names() -> List[str]:
    """Return a sorted list of canon persona names for prompting."""
    names = sorted(get_canon_persona_map().keys())
    app_logger.info(f"Loaded {len(names)} canon persona names for prompting")
    return names


@lru_cache(maxsize=1)
def get_canon_persona_prompt_list() -> List[str]:
    """Return persona names annotated with their phylum for prompt conditioning."""
    persona_map = get_canon_persona_map()
    return [f"{name} ({phylum})" for name, phylum in sorted(persona_map.items())]


@lru_cache(maxsize=1)
def get_generational_by_phylum() -> Dict[str, List[str]]:
    """Extract generational anchors by phylum from SECTION III — GENERATIONS PHYLUM MAP."""
    phylum_path = Path(settings.RJM_DOCS_DIR).resolve() / "Phylum Index MASTER 10-22-25.txt"
    if not phylum_path.exists():
        app_logger.warning("Phylum Index not found at %s", phylum_path)
        return {}

    lines = _safe_read(phylum_path)
    generational_by_phylum: Dict[str, List[str]] = {}
    in_generational_section = False
    current_phylum: str | None = None

    for line in lines:
        stripped = line.strip()
        if "SECTION III — GENERATIONS PHYLUM MAP" in stripped:
            in_generational_section = True
            continue
        if not in_generational_section:
            continue
        if "SECTION" in stripped and "PHYLUM MAP" in stripped and "GENERATIONS" not in stripped:
            # End when next section starts
            break
        # Phylum headers (reuse the same phylum names as SECTION I)
        if stripped and "•" not in stripped and not stripped.startswith("⸻"):
            # Heuristic: treat this as a phylum header if it contains spaces and no digits
            if "(" not in stripped and not stripped.startswith("Sports & Competition"):
                # Some headers like "Sports & Competition" do not include counts here
                pass
            current_phylum = stripped.split("(")[0].strip()
            continue
        if not stripped or stripped.startswith("⸻"):
            continue
        if "•" in stripped and current_phylum:
            parts = [p.strip() for p in stripped.split("•") if p.strip()]
            bucket = generational_by_phylum.setdefault(current_phylum, [])
            for part in parts:
                bucket.append(part)

    app_logger.info(f"Loaded generational anchors for {len(generational_by_phylum)} phyla")
    return generational_by_phylum


@lru_cache(maxsize=1)
def get_local_culture_personas() -> List[str]:
    """Return persona names that act as local culture modules (Community & Local Pride phylum)."""
    persona_map = get_canon_persona_map()
    locals_ = [name for name, phylum in persona_map.items() if phylum == "Community & Local Pride"]
    app_logger.info(f"Loaded {len(locals_)} local culture personas")
    return locals_


