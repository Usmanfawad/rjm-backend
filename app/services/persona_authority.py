"""
PERSONA AUTHORITY — Centralized Governance for RJM Persona Programs

This module is the SINGLE SOURCE OF TRUTH for persona governance.
All persona selection, validation, suppression, and rotation MUST go through this module.

Key Responsibilities:
1. SELECTION: Choose personas from the correct category pool
2. VALIDATION: Ensure all personas are valid for the category
3. SUPPRESSION: Prevent cross-category contamination
4. ROTATION: Ensure freshness and prevent over-indexing (Phase 1 Fix #1)
5. DIVERSITY: Enforce phylum diversity requirements
6. INSIGHT GOVERNANCE: Ensure persona insights reference valid, distinct personas (Phase 1 Fix #2)
7. ALLOWLIST: Strict enforcement of canon, rejecting deprecated personas (Phase 1 Fix #3)

PHASE 1 FIXES:
1. Default persona gravity - rotation pressure / anti-repeat logic
2. Persona Highlights vs Insights - HARD SEPARATION enforced
3. Sunset personas - strict allowlist, no deprecated personas

This module enforces personas as STATEFUL OBJECTS, not just content.

Architecture:
- CategoryPersonaPool: The authoritative list of personas for a category
- PersonaSelectionContext: Tracks what's been selected for a single program
- PersonaAuthority: The main governance class that enforces all rules
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from app.config.logger import app_logger
from app.services.rjm_ingredient_canon import (
    GENERATIONS_BY_COHORT,
    ALL_GENERATIONAL_NAMES,
    ALL_ANCHORS,
    get_category_personas,
    get_dual_anchors,
    get_persona_phylum,
    get_canonical_name,
    is_persona_valid_for_category,
    normalize_generational_name,
    infer_category_with_llm,
    # Phase 1 Fix imports
    is_deprecated_persona,
    is_hot_persona,
    get_rotation_weight,
    # Category pool (simplified - no hardcoded overlays)
    get_flexible_persona_pool,
)


# ════════════════════════════════════════════════════════════════════════════
# GLOBAL ROTATION STATE
# Tracks recently used personas across sessions for freshness
# ════════════════════════════════════════════════════════════════════════════

_GLOBAL_RECENT_PERSONAS: deque[str] = deque(maxlen=200)
_GLOBAL_RECENT_GENERATIONAL: deque[str] = deque(maxlen=60)
_GLOBAL_RECENT_HIGHLIGHT_PERSONAS: deque[str] = deque(maxlen=40)


def _register_used_personas(names: List[str]) -> None:
    """Register personas as recently used for rotation."""
    for name in names:
        if name and name not in _GLOBAL_RECENT_PERSONAS:
            _GLOBAL_RECENT_PERSONAS.append(name)


def _register_used_generational(names: List[str]) -> None:
    """Register generational segments as recently used."""
    for name in names:
        if name and name not in _GLOBAL_RECENT_GENERATIONAL:
            _GLOBAL_RECENT_GENERATIONAL.append(name)


def _register_used_highlights(names: List[str]) -> None:
    """Register highlight personas as recently used (for insight separation)."""
    for name in names:
        if name and name not in _GLOBAL_RECENT_HIGHLIGHT_PERSONAS:
            _GLOBAL_RECENT_HIGHLIGHT_PERSONAS.append(name)


def _is_recently_used(name: str) -> bool:
    """Check if a persona was recently used."""
    return name in _GLOBAL_RECENT_PERSONAS


def _is_recently_highlighted(name: str) -> bool:
    """Check if a persona was recently used in highlights."""
    return name in _GLOBAL_RECENT_HIGHLIGHT_PERSONAS


def clear_rotation_state() -> None:
    """Clear all rotation state (useful for testing)."""
    _GLOBAL_RECENT_PERSONAS.clear()
    _GLOBAL_RECENT_GENERATIONAL.clear()
    _GLOBAL_RECENT_HIGHLIGHT_PERSONAS.clear()


# ════════════════════════════════════════════════════════════════════════════
# PERSONA SELECTION CONTEXT
# Tracks the state of persona selection for a single program generation
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class PersonaSelectionContext:
    """Tracks persona selection state for a single program generation.
    
    This ensures that within a single program:
    - Highlights and insights don't overlap
    - All personas come from the correct category pool
    - Diversity requirements are met
    """
    category: str
    brand_name: str
    brief: str
    
    # Selected personas (names only, for fast lookup)
    selected_portfolio: List[str] = field(default_factory=list)
    selected_highlights: List[str] = field(default_factory=list)
    selected_insights: List[str] = field(default_factory=list)
    selected_generational: List[str] = field(default_factory=list)
    
    # Tracking sets for O(1) lookup
    _portfolio_set: Set[str] = field(default_factory=set)
    _highlight_set: Set[str] = field(default_factory=set)
    _insight_set: Set[str] = field(default_factory=set)
    _phylum_counts: Dict[str, int] = field(default_factory=dict)
    
    def add_to_portfolio(self, name: str) -> bool:
        """Add a persona to the portfolio if not already present."""
        if name in self._portfolio_set:
            return False
        self.selected_portfolio.append(name)
        self._portfolio_set.add(name)
        
        # Track phylum for diversity
        phylum = get_persona_phylum(name)
        if phylum:
            self._phylum_counts[phylum] = self._phylum_counts.get(phylum, 0) + 1
        return True
    
    def add_to_highlights(self, name: str) -> bool:
        """Add a persona to highlights if not already present."""
        if name in self._highlight_set:
            return False
        self.selected_highlights.append(name)
        self._highlight_set.add(name)
        return True
    
    def add_to_insights(self, name: str) -> bool:
        """Add a persona to insights if not already present and not in highlights."""
        if name in self._insight_set or name in self._highlight_set:
            return False
        self.selected_insights.append(name)
        self._insight_set.add(name)
        return True
    
    def is_in_portfolio(self, name: str) -> bool:
        """Check if a persona is in the portfolio."""
        return name in self._portfolio_set
    
    def is_highlight_persona(self, name: str) -> bool:
        """Check if a persona is used in highlights."""
        return name in self._highlight_set
    
    def get_phylum_distribution(self) -> Dict[str, int]:
        """Get current phylum distribution."""
        return dict(self._phylum_counts)
    
    def get_dominant_phylum_ratio(self) -> float:
        """Get the ratio of the most common phylum."""
        if not self._phylum_counts or not self.selected_portfolio:
            return 0.0
        max_count = max(self._phylum_counts.values())
        return max_count / len(self.selected_portfolio)


# ════════════════════════════════════════════════════════════════════════════
# PERSONA AUTHORITY
# The main governance class that enforces all persona rules
# ════════════════════════════════════════════════════════════════════════════

class PersonaAuthority:
    """Centralized authority for persona governance.
    
    Usage:
        authority = PersonaAuthority(category="CPG", brand_name="Gold Bond", brief="...")
        
        # Validate and select personas
        valid_personas = authority.validate_personas(llm_suggested_personas)
        
        # Get highlight personas (ensuring diversity)
        highlights = authority.select_highlights(valid_personas, count=3)
        
        # Get insight personas (must be different from highlights)
        insight_personas = authority.select_for_insights(valid_personas, exclude=highlights)
        
        # Build final portfolio
        portfolio = authority.build_portfolio(valid_personas, target_count=15)
    """
    
    def __init__(
        self,
        category: str,
        brand_name: str,
        brief: str,
        min_phyla: int = 3,
        max_phylum_dominance: float = 0.35,
    ):
        self.category = category
        self.brand_name = brand_name
        self.brief = brief
        self.min_phyla = min_phyla
        self.max_phylum_dominance = max_phylum_dominance
        
        # Pure category pool (no hardcoded overlays - LLM handles meaning understanding)
        self.category_pool = get_flexible_persona_pool(category, brand_name, brief)
        self.category_pool_set = set(self.category_pool)

        # Get category anchors
        self.anchors = get_dual_anchors(brand_name, category)
        
        # Create selection context
        self.context = PersonaSelectionContext(
            category=category,
            brand_name=brand_name,
            brief=brief,
        )
        
        app_logger.info(
            f"PersonaAuthority initialized: category={category}, "
            f"pool_size={len(self.category_pool)}, anchors={self.anchors}"
        )

    def _is_allowed_persona(self, name: str) -> bool:
        """Allow personas that pass category check OR are in the category pool (for dual-anchor brands)."""
        if not name:
            return False
        if is_deprecated_persona(name):
            return False

        canonical = get_canonical_name(name)

        # Category guardrail
        if is_persona_valid_for_category(canonical, self.category):
            return True

        # Also allow if in the category pool (handles dual-anchor brands like Uber)
        return canonical in self.category_pool_set or name in self.category_pool_set
    
    def validate_persona(self, name: str) -> Tuple[bool, str, Optional[str]]:
        """Validate a single persona against category constraints.
        
        PHASE 1 FIX #3: Also checks for deprecated/sunset personas.
        
        Returns:
            (is_valid, canonical_name, rejection_reason)
        """
        if not name:
            return False, name, "Empty name"
        
        # Skip anchors
        if name in ALL_ANCHORS or name.startswith("RJM "):
            return False, name, "Anchor segment (not a core persona)"
        
        # Skip generational segments
        if name in ALL_GENERATIONAL_NAMES:
            return False, name, "Generational segment (handled separately)"
        
        # PHASE 1 FIX #3: Check for deprecated personas
        if is_deprecated_persona(name):
            return False, name, f"Deprecated/sunset persona '{name}' - not in active canon"
        
        # Get canonical name
        canonical = get_canonical_name(name)
        
        # Also check canonical form for deprecation
        if is_deprecated_persona(canonical):
            return False, name, f"Deprecated/sunset persona '{canonical}' - not in active canon"
        
        # Category guardrail
        if not self._is_allowed_persona(canonical):
            return False, name, f"Not valid for category '{self.category}'"
        
        return True, canonical, None
    
    def validate_personas(
        self,
        persona_names: List[str],
        log_rejections: bool = True
    ) -> List[str]:
        """Validate a list of personas against category constraints.
        
        Returns only the valid personas (in canonical form).
        """
        valid = []
        rejected = []
        seen = set()
        
        for name in persona_names:
            is_valid, canonical, reason = self.validate_persona(name)
            
            if not is_valid:
                rejected.append((name, reason))
                continue
            
            if canonical in seen:
                continue
            
            seen.add(canonical)
            valid.append(canonical)
        
        if log_rejections and rejected:
            app_logger.warning(
                f"PersonaAuthority rejected {len(rejected)} personas: "
                f"{rejected[:5]}..."
            )
        
        return valid
    
    def select_highlights(
        self,
        available_personas: List[str],
        count: int = 4,
        prefer_fresh: bool = True
    ) -> List[str]:
        """Select personas for highlights, ensuring diversity and freshness.
        
        PHASE 1 FIX #1: Applies rotation pressure to avoid "hot" personas
        that appear too frequently (e.g., Romantic Voyager in Travel).
        
        PHASE 1 FIX #2: Selected personas are tracked and MUST NOT appear
        in insights section.
        
        PHASE 1 FIX (NEW): Hot persona clustering prevention - max 1 hot persona
        in highlights for Travel & Hospitality to break the Romantic Voyager /
        Retreat Seeker / Island Hopper cluster.
        
        Rules:
        - Must be from category pool
        - Prefer personas not recently highlighted
        - Apply rotation weight (hot personas get penalty)
        - Ensure phylum diversity
        - MAX 1 hot persona per highlight set (for Travel & Hospitality)
        - Return up to `count` personas
        """
        import random
        
        selected = []
        phyla_used = set()
        hot_count = 0  # Track hot personas selected
        
        # Max hot personas allowed in highlights
        # For Travel & Hospitality: limit to 1 to break clustering
        max_hot = 1 if self.category == "Travel & Hospitality" else 2
        
        # Build weighted candidate list with rotation pressure
        candidates = []
        for name in available_personas:
            # Skip deprecated personas
            if is_deprecated_persona(name):
                continue
            
            # Must be allowed via category guardrail or meaning overlays
            if not self._is_allowed_persona(name):
                continue
            
            # Calculate rotation weight
            recency_pos = -1
            if prefer_fresh and name in _GLOBAL_RECENT_HIGHLIGHT_PERSONAS:
                recency_pos = list(_GLOBAL_RECENT_HIGHLIGHT_PERSONAS).index(name)
            
            weight = get_rotation_weight(name, self.category, recency_pos)
            
            # PHASE 1 FIX #1: Extra penalty if in global recent highlights
            if _is_recently_highlighted(name):
                weight *= 0.5
            
            candidates.append((name, weight, get_persona_phylum(name)))
        
        # Sort by weight (highest first) with randomization for equal weights
        candidates.sort(key=lambda x: (-x[1], random.random()))
        
        for name, weight, phylum in candidates:
            if len(selected) >= count:
                break
            
            # Ensure phylum diversity (no more than 1 from same phylum in highlights)
            if phylum and phylum in phyla_used and len(selected) < 2:
                continue  # Allow overlap only after we have at least 2
            
            # PHASE 1 FIX: Hot persona clustering prevention
            # Limit hot personas in highlights to prevent the same cluster appearing
            if is_hot_persona(name, self.category) and hot_count >= max_hot:
                app_logger.debug(
                    f"Skipping hot persona '{name}' - already have {hot_count} hot personas in highlights"
                )
                continue
            
            selected.append(name)
            self.context.add_to_highlights(name)  # PHASE 1 FIX #2: Track for insight exclusion
            if phylum:
                phyla_used.add(phylum)
            if is_hot_persona(name, self.category):
                hot_count += 1
        
        # Register for rotation
        _register_used_highlights(selected)
        
        app_logger.info(
            f"Selected {len(selected)} highlight personas with rotation: {selected} "
            f"(hot personas: {hot_count}/{max_hot} max allowed)"
        )
        return selected
    
    def select_for_insights(
        self,
        available_personas: List[str],
        count: int = 2,
        must_be_different_from_highlights: bool = True
    ) -> List[str]:
        """Select personas for insights, ensuring they're different from highlights.
        
        PHASE 1 FIX #2: CRITICAL ENFORCEMENT
        Insights MUST NOT reference the same personas as highlights.
        This is enforced as a HARD RULE, not a suggestion.
        """
        selected = []
        
        # PHASE 1 FIX #2: Build explicit exclusion set from highlights
        highlight_exclusion = set(self.context.selected_highlights)
        
        for name in available_personas:
            if len(selected) >= count:
                break
            
            # Skip deprecated personas
            if is_deprecated_persona(name):
                continue
            
            # Must be allowed via category guardrail or meaning overlays
            if not self._is_allowed_persona(name):
                continue
            
            # PHASE 1 FIX #2: HARD RULE - Must not be in highlights
            if must_be_different_from_highlights:
                if name in highlight_exclusion:
                    app_logger.debug(f"Insight exclusion: '{name}' already in highlights")
                    continue
                if self.context.is_highlight_persona(name):
                    app_logger.debug(f"Insight exclusion: '{name}' marked as highlight")
                    continue
            
            # Also avoid recently highlighted personas globally for freshness
            if _is_recently_highlighted(name):
                continue
            
            if self.context.add_to_insights(name):
                selected.append(name)
        
        # Log enforcement status
        if highlight_exclusion:
            app_logger.info(
                f"PHASE 1 FIX #2: Selected {len(selected)} insight personas: {selected}, "
                f"excluded {len(highlight_exclusion)} highlight personas: {list(highlight_exclusion)}"
            )
        else:
            app_logger.info(f"Selected {len(selected)} insight personas: {selected}")
        
        return selected
    
    def validate_insight_text(self, insight_text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate that an insight references a valid portfolio persona.
        
        PHASE 1 FIX #2: Enforces hard separation from highlights.
        PHASE 1 FIX #3: Rejects deprecated personas.
        
        Returns:
            (is_valid, extracted_persona_name, error_message)
        """
        # Extract persona name from insight - multiple formats:
        # - "...are 'Persona Name'."
        # - "...are 'Persona Name'"
        # - "...reflecting the 'Persona Name' persona."
        # - "...indicative of the 'Persona Name' mindset."
        # Try multiple patterns to catch all formats
        match = None
        
        # Pattern 1: Quoted name at end (with optional period)
        match = re.search(r'["\']([^"\']+)["\']\.?$', insight_text)
        
        # Pattern 2: Quoted name followed by "persona" or "mindset" etc.
        if not match:
            match = re.search(r'["\']([^"\']+)["\'](?:\s+(?:persona|mindset|segment|type))?\.?$', insight_text)
        
        # Pattern 3: Any quoted name in the text (fallback)
        if not match:
            match = re.search(r'["\']([^"\']+)["\']', insight_text)
        
        if not match:
            return True, None, None  # No persona mentioned, that's okay
        
        persona_name = match.group(1)
        
        # Handle pluralized persona names (e.g., "Caffeine Fiends" -> "Caffeine Fiend")
        singular_name = persona_name.rstrip('s') if persona_name.endswith('s') and not persona_name.endswith('ss') else persona_name
        # Also handle "ies" -> "y" plurals (e.g., "Buddies" -> "Buddy")
        if singular_name.endswith('ie') and persona_name.endswith('ies'):
            singular_name = singular_name[:-2] + 'y'
        
        # Try canonical lookup with both forms
        canonical = get_canonical_name(persona_name)
        if not is_persona_valid_for_category(canonical, self.category):
            canonical = get_canonical_name(singular_name)
        
        # PHASE 1 FIX #3: Check for deprecated personas
        if is_deprecated_persona(canonical):
            return False, persona_name, f"Persona '{persona_name}' is deprecated/sunset"
        
        # Validate against category guardrail
        if not self._is_allowed_persona(canonical):
            return False, persona_name, f"Persona '{persona_name}' not valid for category '{self.category}'"
        
        # Check if it's in the portfolio (try both original and singular forms)
        in_portfolio = self.context.is_in_portfolio(canonical)
        if not in_portfolio and singular_name != persona_name:
            in_portfolio = self.context.is_in_portfolio(get_canonical_name(singular_name))
        if not in_portfolio:
            return False, persona_name, f"Persona '{persona_name}' not in portfolio"
        
        # PHASE 1 FIX #2: HARD RULE - Check if it's in highlights (check both forms)
        is_highlight = self.context.is_highlight_persona(canonical)
        if not is_highlight and singular_name != persona_name:
            is_highlight = self.context.is_highlight_persona(get_canonical_name(singular_name))
        
        if is_highlight:
            return False, persona_name, f"PHASE 1 VIOLATION: Persona '{persona_name}' already in highlights - insights MUST use different personas"
        
        return True, persona_name, None
    
    def fix_insight_persona(self, insight_text: str) -> str:
        """Fix an insight by replacing an invalid persona with a valid one.
        
        If the insight references an invalid or highlighted persona,
        replace it with a valid portfolio persona.
        """
        is_valid, persona_name, error = self.validate_insight_text(insight_text)
        
        if is_valid:
            return insight_text
        
        # Find a replacement persona
        replacement = None
        for name in self.context.selected_portfolio:
            if not self.context.is_highlight_persona(name) and name not in self.context._insight_set:
                replacement = name
                break
        
        if not replacement and self.context.selected_portfolio:
            # Fall back to any portfolio persona not in insights
            for name in self.context.selected_portfolio:
                if name not in self.context._insight_set:
                    replacement = name
                    break
        
        if replacement and persona_name:
            # Replace the persona name in the insight (handle both single and double quotes)
            # Handle various formats:
            # - 'Persona Name'
            # - "Persona Name"
            # - 'Persona Name' persona.
            # - 'Persona Name' mindset.
            
            if f"'{persona_name}'" in insight_text:
                # Single quotes - replace the exact quoted name
                fixed = insight_text.replace(f"'{persona_name}'", f"'{replacement}'")
            elif f'"{persona_name}"' in insight_text:
                # Double quotes - replace the exact quoted name
                fixed = insight_text.replace(f'"{persona_name}"', f'"{replacement}"')
            else:
                # Fallback: try to replace any occurrence
                fixed = insight_text.replace(persona_name, replacement)
            
            self.context.add_to_insights(replacement)
            app_logger.info(
                f"PHASE 1 FIX #2: Fixed insight - replaced '{persona_name}' with '{replacement}' (was in highlights)"
            )
            return fixed
        
        return insight_text
    
    def build_portfolio(
        self,
        llm_personas: List[str],
        target_count: int = 15
    ) -> List[str]:
        """Build the final persona portfolio with governance rules applied.
        
        Rules:
        1. Start with LLM suggestions (validated)
        2. Fill to target from category pool
        3. Ensure phylum diversity
        4. Apply rotation (prefer fresh personas)
        """
        # Validate LLM suggestions
        valid_llm = self.validate_personas(llm_personas)
        
        # Add to context
        for name in valid_llm:
            self.context.add_to_portfolio(name)
        
        # Check if we need more
        current_count = len(self.context.selected_portfolio)
        
        if current_count < target_count:
            # Fill from category pool with rotation and diversity
            available = [
                name for name in self.category_pool
                if name not in self.context._portfolio_set
            ]
            
            # Sort by freshness (non-recent first)
            available.sort(key=lambda p: (1 if _is_recently_used(p) else 0))
            
            for name in available:
                if len(self.context.selected_portfolio) >= target_count:
                    break
                
                # Check phylum diversity
                phylum = get_persona_phylum(name)
                if phylum:
                    phylum_count = self.context._phylum_counts.get(phylum, 0)
                    new_count = phylum_count + 1
                    new_total = len(self.context.selected_portfolio) + 1
                    new_ratio = new_count / new_total
                    
                    # Skip if this would violate dominance rule
                    if new_ratio > self.max_phylum_dominance and len(self.context._phylum_counts) >= self.min_phyla:
                        continue
                
                self.context.add_to_portfolio(name)
        
        # Register for rotation
        _register_used_personas(self.context.selected_portfolio)
        
        # Log diversity stats
        phylum_dist = self.context.get_phylum_distribution()
        app_logger.info(
            f"Built portfolio: {len(self.context.selected_portfolio)} personas, "
            f"{len(phylum_dist)} phyla, dominance={self.context.get_dominant_phylum_ratio():.2f}"
        )
        
        return list(self.context.selected_portfolio)
    
    def select_generational(self, llm_suggestions: List[str]) -> List[str]:
        """Select generational segments (one per cohort).
        
        Rules:
        - Must have one from each cohort: Gen Z, Millennial, Gen X, Boomer
        - Prefer LLM suggestions if valid
        - Apply rotation for freshness
        """
        selected = []
        cohorts_covered = set()
        
        # Process LLM suggestions first
        for name in llm_suggestions:
            canonical = normalize_generational_name(name)
            if not canonical:
                continue
            
            # Determine cohort
            cohort = None
            for c in GENERATIONS_BY_COHORT.keys():
                if canonical.startswith(c):
                    cohort = c
                    break
            
            if cohort and cohort not in cohorts_covered:
                selected.append(canonical)
                cohorts_covered.add(cohort)
                self.context.selected_generational.append(canonical)
        
        # Fill missing cohorts
        for cohort, segments in GENERATIONS_BY_COHORT.items():
            if cohort in cohorts_covered:
                continue
            
            # Prefer non-recent segments
            for seg in segments:
                if seg not in _GLOBAL_RECENT_GENERATIONAL:
                    selected.append(seg)
                    cohorts_covered.add(cohort)
                    self.context.selected_generational.append(seg)
                    break
            else:
                # All recent, just use first
                selected.append(segments[0])
                cohorts_covered.add(cohort)
                self.context.selected_generational.append(segments[0])
        
        # Register for rotation
        _register_used_generational(selected)
        
        return selected[:4]  # Max 4 (one per cohort)
    
    def get_full_portfolio(self) -> List[str]:
        """Get the complete portfolio including anchors and generational."""
        return (
            self.context.selected_portfolio[:15] +
            self.anchors[:2] +
            self.context.selected_generational[:4]
        )


# ════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def create_authority(
    brand_name: str,
    brief: str,
    category: Optional[str] = None
) -> PersonaAuthority:
    """Create a PersonaAuthority for the given context.
    
    If category is not provided, it will be inferred from brand_name and brief.
    """
    if not category:
        category = infer_category_with_llm(brand_name, brief)
    
    return PersonaAuthority(
        category=category,
        brand_name=brand_name,
        brief=brief,
    )


def get_category_persona_pool_for_prompt(category: str, limit: int = 30) -> str:
    """Get a formatted string of category personas for use in prompts.
    
    This should be used instead of hardcoded persona lists in prompts.
    """
    pool = get_category_personas(category)
    if not pool:
        return "No personas available for this category"
    
    return ", ".join(pool[:limit])


def validate_conversation_persona_mention(
    persona_name: str,
    category: str
) -> Tuple[bool, str]:
    """Validate a persona mentioned in conversation against category rules.
    
    Use this when the LLM mentions a persona in conversation text.
    Returns (is_valid, canonical_name_or_error_message)
    """
    if not persona_name:
        return False, "Empty persona name"
    
    canonical = get_canonical_name(persona_name)
    
    if not is_persona_valid_for_category(canonical, category):
        valid_examples = get_category_personas(category)[:5]
        return False, f"'{persona_name}' is not valid for {category}. Use: {', '.join(valid_examples)}"
    
    return True, canonical

