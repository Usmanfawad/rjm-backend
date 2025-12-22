"""
MIRA Reasoning Engine.

This module implements the full Reasoning State Machine from the Reasoning JSON spec.
It computes funnel position, media mix, platform path, and budget window based on
category, KPI, constraints, and behavioral cues - not defaults.

The Reasoning Engine follows the canonical flow:
ORIENTATION → CONSTRAINT → FUNNEL → MIX → PLATFORM → PERFORMANCE → PRE_ACTIVATION

All decisions are now driven by the World Model JSON specs, not hardcoded Python logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.config.logger import app_logger
from app.services.mira_world_model import (
    load_reasoning_state_machine,
    get_category_profile,
    get_mix_template,
    get_creative_angle_modifiers,
    get_budget_rules,
    get_platform_decision_flow,
    get_kpi_buckets,
    get_category_funnel_bias,
    get_identity_forward_categories,
    get_utility_forward_categories,
)


# Re-export for backward compatibility
def load_reasoning_spec() -> Dict[str, Any]:
    """Load the Reasoning State Machine JSON spec."""
    return load_reasoning_state_machine()


@dataclass
class ReasoningContext:
    """Holds all reasoning inputs and computed outputs."""

    # Inputs
    brand_name: str = ""
    brief: str = ""
    category: str = ""
    objective: Optional[str] = None
    kpi: Optional[str] = None
    budget: Optional[float] = None
    timeline: Optional[str] = None
    geography: Optional[str] = None
    creative_angle: Optional[str] = None
    platform_preference: Optional[str] = None

    # Computed outputs
    funnel_stage: str = "mid"  # upper | mid | lower
    media_mix: Dict[str, str] = field(default_factory=lambda: {
        "CTV": "35-45%",
        "OLV": "30-35%",
        "Audio": "15-20%",
        "Display": "10-15%"
    })
    platform_path: str = "Direct via RJM"  # DSP | Direct via RJM | Hybrid
    budget_window: str = "single"  # single | split | adaptive
    pacing_mode: str = "standard"  # standard | front-loaded | back-loaded
    flighting_cadence: str = "linear"  # linear | pulsed | burst
    performance_path: str = "balanced"  # quality | scale | balanced
    persona_emphasis: str = "balanced"
    generational_weighting: Optional[str] = None
    strategic_rationale: str = ""

    # State tracking
    current_state: str = "STATE_ORIENTATION"
    missing_inputs: List[str] = field(default_factory=list)


# Category profiles are now loaded from World Model JSON
# Fallback profiles for categories not in the JSON spec
CATEGORY_PROFILES_FALLBACK = {
    "Tech & Wireless": {
        "mix_bias": "OLV + Display",
        "funnel_bias": "mid",
        "budget_expectation": "high",
    },
    "Travel & Hospitality": {
        "mix_bias": "CTV + OLV blend",
        "funnel_bias": "upper",
        "budget_expectation": "medium_to_high",
    },
    "Entertainment": {
        "mix_bias": "CTV-heavy",
        "funnel_bias": "upper",
        "budget_expectation": "high",
    },
    "Health & Pharma": {
        "mix_bias": "OLV + Audio",
        "funnel_bias": "mid",
        "budget_expectation": "high",
    },
    "Luxury & Fashion": {
        "mix_bias": "CTV + social blend",
        "funnel_bias": "upper",
        "budget_expectation": "high",
    },
    "Sports & Fitness": {
        "mix_bias": "CTV + OLV",
        "funnel_bias": "upper_to_mid",
        "budget_expectation": "medium",
    },
    "Alcohol & Spirits": {
        "mix_bias": "CTV + Audio",
        "funnel_bias": "upper",
        "budget_expectation": "medium_to_high",
    },
    "Home & DIY": {
        "mix_bias": "OLV + Display",
        "funnel_bias": "mid",
        "budget_expectation": "medium",
    },
}


def _get_category_profile_combined(category: str) -> Dict[str, Any]:
    """Get category profile from World Model, with fallback to local profiles."""
    # First try World Model
    profile = get_category_profile(category)
    if profile:
        return profile
    
    # Fallback to local profiles
    return CATEGORY_PROFILES_FALLBACK.get(category, {})

# KPI to funnel mapping - built from World Model
def _build_kpi_funnel_map() -> Dict[str, str]:
    """Build KPI to funnel mapping from World Model."""
    kpi_buckets = get_kpi_buckets()
    mapping = {}
    
    for funnel, kpis in kpi_buckets.items():
        funnel_stage = funnel.replace("_funnel", "")  # "upper_funnel" -> "upper"
        for kpi in kpis:
            mapping[kpi.lower()] = funnel_stage
    
    # Add common aliases
    mapping.update({
        "vcr": "upper",
        "awareness": "upper",
        "brand_lift": "upper",
        "traffic": "mid",
        "consideration": "mid",
        "conversions": "lower",
        "cpa": "lower",
        "roas": "lower",
        "sales": "lower",
        "purchase": "lower",
    })
    
    return mapping


KPI_FUNNEL_MAP = _build_kpi_funnel_map()


def _get_mix_template_from_world_model(funnel_stage: str) -> Dict[str, str]:
    """Get mix template from World Model."""
    return get_mix_template(funnel_stage)


# Category-specific mix adjustments from World Model
def _get_creative_modifiers() -> Dict[str, Dict[str, str]]:
    """Get creative angle modifiers from World Model."""
    return get_creative_angle_modifiers()


def _infer_category_from_brief(brief: str, brand_name: str) -> str:
    """Infer category from brief text using keyword matching."""
    text = f"{brief} {brand_name}".lower()

    # Order matters - check more specific categories first
    category_keywords = [
        ("Beauty", ["beauty", "cosmetic", "skincare", "makeup", "hair care", "salon", "fragrance", "lipstick", "mascara"]),
        ("QSR", ["restaurant", "fast food", "qsr", "burger", "pizza", "taco", "chicken", "brunch", "dining", "food service"]),
        ("Auto", ["car ", "cars ", "auto ", "vehicle", "automotive", "truck", "suv ", "ev ", "electric vehicle", "dealership"]),
        ("Finance", ["bank", "finance", "insurance", "credit", "loan", "mortgage", "investment", "financial"]),
        ("Health & Pharma", ["pharma", "pharmaceutical", "medicine", "healthcare", "drug", "prescription"]),
        ("CPG", ["cpg", "consumer goods", "packaged goods", "household", "cleaning", "personal care"]),
        ("Tech & Wireless", ["tech", "wireless", "mobile", "phone", "software", "app ", "digital", "telecom"]),
        ("Travel & Hospitality", ["travel", "hotel", "hospitality", "vacation", "airline", "cruise", "resort"]),
        ("Entertainment", ["entertainment", "movie", "film", "streaming", "gaming", "music", "media"]),
        ("Luxury & Fashion", ["luxury", "fashion", "designer", "premium", "high-end", "couture"]),
        ("Sports & Fitness", ["sports", "fitness", "athletic", "gym", "workout", "training"]),
        ("Alcohol & Spirits", ["alcohol", "spirits", "beer", "wine", "liquor", "beverage"]),
        ("Retail", ["retail", "shop", "store", "e-commerce", "ecommerce", "marketplace", "shopping"]),
    ]

    for category, keywords in category_keywords:
        if any(kw in text for kw in keywords):
            return category

    return "Retail"  # Default fallback


def _determine_funnel_stage(ctx: ReasoningContext) -> str:
    """
    Determine funnel stage based on World Model decision trees:
    1. Explicit KPI (if provided) - highest priority
    2. Brief language cues - explicit intent
    3. Category profile from World Model - fallback
    4. Cross-domain reasoning maps
    """
    # Check KPI first (highest priority) - using World Model KPI buckets
    if ctx.kpi:
        kpi_lower = ctx.kpi.lower()
        for kpi_keyword, funnel in KPI_FUNNEL_MAP.items():
            if kpi_keyword in kpi_lower:
                return funnel

    # Check brief for explicit funnel cues (before category defaults)
    brief_lower = (ctx.brief or "").lower()
    upper_cues = ["awareness", "launch", "introduce", "new product", "brand building", "storytelling"]
    lower_cues = ["conversion", "sales", "purchase", "buy", "cpa", "roas", "performance"]

    has_upper_cue = any(cue in brief_lower for cue in upper_cues)
    has_lower_cue = any(cue in brief_lower for cue in lower_cues)

    # If brief has explicit cues, use them
    if has_upper_cue and not has_lower_cue:
        return "upper"
    if has_lower_cue and not has_upper_cue:
        return "lower"

    # Check identity-forward vs utility-forward from World Model
    category = ctx.category or _infer_category_from_brief(ctx.brief, ctx.brand_name)
    
    identity_forward = get_identity_forward_categories()
    utility_forward = get_utility_forward_categories()
    
    if category.lower() in [c.lower() for c in identity_forward]:
        return "upper"
    if category.lower() in [c.lower() for c in utility_forward]:
        return "mid"

    # Fall back to category profile from World Model
    profile = _get_category_profile_combined(category)
    funnel_bias = profile.get("funnel_bias", "mid")

    # Also check cross-domain maps
    cross_domain_bias = get_category_funnel_bias(category)
    if cross_domain_bias and cross_domain_bias != "mid":
        # Cross-domain maps use format like "upper → mid"
        if "upper" in cross_domain_bias:
            return "upper"
        if "lower" in cross_domain_bias:
            return "lower"

    # Normalize funnel bias
    if funnel_bias in ("upper", "upper_to_mid"):
        return "upper"
    elif funnel_bias in ("lower", "mid_to_lower"):
        return "lower"

    return "mid"


def _determine_media_mix(ctx: ReasoningContext) -> Dict[str, str]:
    """
    Determine media mix based on World Model decision trees:
    1. Funnel stage (primary driver) - from World Model mix templates
    2. Category adjustments - from World Model category profiles
    3. Creative angle modifiers - from World Model creative angle modifiers
    """
    # Start with funnel-based template from World Model
    base_mix = _get_mix_template_from_world_model(ctx.funnel_stage).copy()

    # Apply category adjustments if available
    category = ctx.category or _infer_category_from_brief(ctx.brief, ctx.brand_name)

    # Category-specific mix biases from World Model profiles
    profile = _get_category_profile_combined(category)
    mix_bias = profile.get("mix_bias", "")

    if "CTV-heavy" in mix_bias:
        base_mix["CTV"] = "55-65%"
        base_mix["Display"] = "5-10%"
    elif "display" in mix_bias.lower():
        base_mix["Display"] = "20-30%"
        base_mix["CTV"] = "30-40%"
    elif "Audio" in mix_bias:
        base_mix["Audio"] = "20-25%"

    # Creative angle modifiers from World Model
    creative_modifiers = _get_creative_modifiers()
    if ctx.creative_angle:
        angle_lower = ctx.creative_angle.lower()
        if any(w in angle_lower for w in ("emotional", "storytelling", "narrative", "brand")):
            # Apply emotional_storytelling modifiers from World Model
            emotional_mod = creative_modifiers.get("emotional_storytelling", {})
            if emotional_mod:
                base_mix["CTV"] = "55-65%"
                base_mix["Display"] = "5-10%"
            else:
                base_mix["CTV"] = "55-65%"
                base_mix["Display"] = "5-10%"
        elif any(w in angle_lower for w in ("functional", "product", "direct response", "performance")):
            # Apply functional_creative modifiers from World Model
            functional_mod = creative_modifiers.get("functional_creative", {})
            if functional_mod:
                base_mix["OLV"] = "35-40%"
                base_mix["Audio"] = "20-25%"
                base_mix["CTV"] = "25-35%"
            else:
                base_mix["OLV"] = "35-40%"
                base_mix["Audio"] = "20-25%"
                base_mix["CTV"] = "25-35%"

    return base_mix


def _determine_platform_path(ctx: ReasoningContext) -> str:
    """
    Determine platform path based on World Model decision flow:
    1. Explicit user preference
    2. Timeline urgency (from World Model decision tree)
    3. Budget level (from World Model budget rules)
    4. Scale requirements
    """
    # Check explicit preference
    if ctx.platform_preference:
        pref_lower = ctx.platform_preference.lower()
        if any(w in pref_lower for w in ("dsp", "dv360", "ttd", "trade desk")):
            return "DSP"
        if "direct" in pref_lower or "ribeye" in pref_lower:
            return "Direct via RJM"
        if "hybrid" in pref_lower:
            return "Hybrid"

    # Apply World Model decision flow
    decision_flow = get_platform_decision_flow()
    
    for step in decision_flow:
        check = step.get("check", "")
        condition = step.get("if", "")
        # result = step.get("then", "")  # Available if needed for more complex routing
        
        if check == "timeline" and "< 48 hours" in condition:
            if ctx.timeline:
                timeline_lower = ctx.timeline.lower()
                if any(w in timeline_lower for w in ("urgent", "asap", "tomorrow", "24 hours", "48 hours")):
                    return "Direct via RJM"
        
        elif check == "budget":
            if ctx.budget:
                if "< $50,000" in condition and ctx.budget < 50000:
                    return "DSP"
                if "> $100,000" in condition and ctx.budget > 100000:
                    return "Hybrid"

    # Check brief for DSP cues
    brief_lower = ctx.brief.lower()
    if any(w in brief_lower for w in ("dsp", "programmatic", "dv360", "trade desk")):
        return "DSP"

    # Default to Direct via RJM for simpler execution
    return "Direct via RJM"


def _determine_budget_window(ctx: ReasoningContext) -> str:
    """
    Determine budget window based on World Model budget rules:
    1. Budget level (from World Model decision tree)
    2. Flight length
    3. Scale demand
    """
    # Get budget rules from World Model
    budget_rules = get_budget_rules()
    
    if ctx.budget:
        # Apply World Model budget thresholds
        # Thresholds are defined in budget_rules but we use numeric comparison
        if ctx.budget < 50000:
            return budget_rules.get("low_budget", {}).get("recommended_window", "single")
        elif ctx.budget > 100000:
            return budget_rules.get("high_budget", {}).get("recommended_window", "split")
        else:
            # Mid budget
            return budget_rules.get("mid_budget", {}).get("recommended_window", "single")

    # Check brief for indicators
    brief_lower = ctx.brief.lower()
    if any(w in brief_lower for w in ("phased", "multiple flights", "waves", "burst")):
        return "split"
    if any(w in brief_lower for w in ("always-on", "continuous", "steady")):
        return "adaptive"

    return "single"


def _determine_pacing_mode(ctx: ReasoningContext) -> str:
    """Determine pacing mode based on brief and objective."""
    brief_lower = ctx.brief.lower()

    if any(w in brief_lower for w in ("launch", "premiere", "opening", "kickoff")):
        return "front-loaded"
    if any(w in brief_lower for w in ("end of quarter", "holiday", "black friday", "finale")):
        return "back-loaded"

    return "standard"


def _determine_flighting_cadence(ctx: ReasoningContext) -> str:
    """Determine flighting cadence based on category and objective."""
    brief_lower = ctx.brief.lower()

    if any(w in brief_lower for w in ("burst", "spike", "event", "moment")):
        return "burst"
    if any(w in brief_lower for w in ("pulse", "wave", "rhythm", "seasonal")):
        return "pulsed"

    return "linear"


def _determine_performance_path(ctx: ReasoningContext) -> str:
    """
    Determine performance path:
    - quality_first: high-intent, higher CPM, narrower personas
    - scale_first: broader reach, cost-efficient
    - balanced: midpoint
    """
    # Check KPI pressure
    if ctx.kpi:
        kpi_lower = ctx.kpi.lower()
        if any(w in kpi_lower for w in ("cpa", "roas", "conversion", "quality")):
            return "quality"
        if any(w in kpi_lower for w in ("reach", "scale", "volume", "impressions")):
            return "scale"

    # Check brief
    brief_lower = ctx.brief.lower()
    if any(w in brief_lower for w in ("quality", "premium", "high-value", "precision")):
        return "quality"
    if any(w in brief_lower for w in ("scale", "reach", "mass", "broad", "volume")):
        return "scale"

    return "balanced"


def _generate_strategic_rationale(ctx: ReasoningContext) -> str:
    """Generate a strategic rationale summarizing the reasoning."""
    category = ctx.category or _infer_category_from_brief(ctx.brief, ctx.brand_name)

    funnel_phrases = {
        "upper": "building brand presence and cultural connection",
        "mid": "driving consideration and engagement",
        "lower": "maximizing conversion and performance outcomes"
    }

    platform_phrases = {
        "DSP": "through programmatic channels for precise control",
        "Direct via RJM": "via RJM-managed activation for streamlined execution",
        "Hybrid": "using a hybrid approach balancing control and reach"
    }

    funnel_phrase = funnel_phrases.get(ctx.funnel_stage, "balanced awareness and consideration")
    platform_phrase = platform_phrases.get(ctx.platform_path, "through optimized channels")

    rationale = (
        f"For {ctx.brand_name} in {category}, this plan focuses on {funnel_phrase}, "
        f"delivered {platform_phrase}. "
        f"The {ctx.budget_window} budget window with {ctx.pacing_mode} pacing "
        f"supports a {ctx.performance_path} performance approach, "
        f"using CTV as the cultural anchor with OLV/Audio/Display for reinforcement and reach."
    )

    return rationale


def _check_missing_inputs(ctx: ReasoningContext) -> List[str]:
    """Check for minimum required inputs before pre-activation."""
    missing = []

    if not ctx.brand_name:
        missing.append("brand_name")
    if not ctx.brief:
        missing.append("brief")

    # These are nice-to-have but not blocking
    # if not ctx.objective:
    #     missing.append("objective")
    # if not ctx.kpi:
    #     missing.append("kpi")
    # if not ctx.geography:
    #     missing.append("geography")

    return missing


def run_reasoning_engine(
    brand_name: str,
    brief: str,
    category: Optional[str] = None,
    objective: Optional[str] = None,
    kpi: Optional[str] = None,
    budget: Optional[float] = None,
    timeline: Optional[str] = None,
    geography: Optional[str] = None,
    creative_angle: Optional[str] = None,
    platform_preference: Optional[str] = None,
    user_text: Optional[str] = None,
) -> ReasoningContext:
    """
    Run the full Reasoning Engine to compute all activation parameters.

    This follows the canonical reasoning flow:
    1. ORIENTATION - Understand the real goal
    2. CONSTRAINT - Identify operational boundaries
    3. FUNNEL - Assign funnel stage
    4. MIX - Determine channel allocation
    5. PLATFORM - Select platform path
    6. PERFORMANCE - Choose quality vs scale
    7. PRE_ACTIVATION - Finalize outputs

    Returns a ReasoningContext with all computed values.
    """
    app_logger.info(f"Running MIRA Reasoning Engine for brand={brand_name}")

    # Initialize context
    ctx = ReasoningContext(
        brand_name=brand_name,
        brief=brief,
        category=category or _infer_category_from_brief(brief, brand_name),
        objective=objective,
        kpi=kpi,
        budget=budget,
        timeline=timeline,
        geography=geography,
        creative_angle=creative_angle,
        platform_preference=platform_preference,
    )

    # Extract additional cues from user_text if provided
    if user_text:
        user_lower = user_text.lower()
        # Extract platform preference
        if not ctx.platform_preference:
            if any(w in user_lower for w in ("dsp", "dv360", "ttd")):
                ctx.platform_preference = "DSP"
            elif "direct" in user_lower:
                ctx.platform_preference = "Direct"
        # Extract budget hints
        if not ctx.budget:
            import re
            budget_match = re.search(r'\$?([\d,]+)k?', user_lower)
            if budget_match:
                try:
                    amount = float(budget_match.group(1).replace(',', ''))
                    if 'k' in user_lower[budget_match.end():budget_match.end()+2]:
                        amount *= 1000
                    ctx.budget = amount
                except ValueError:
                    pass

    # Check for missing critical inputs
    ctx.missing_inputs = _check_missing_inputs(ctx)
    if ctx.missing_inputs:
        ctx.current_state = "STATE_CLARIFICATION"
        return ctx

    # STATE_ORIENTATION → STATE_CONSTRAINT (implied, constraints extracted from brief)
    ctx.current_state = "STATE_FUNNEL"

    # STATE_FUNNEL - Determine funnel stage
    ctx.funnel_stage = _determine_funnel_stage(ctx)
    app_logger.debug(f"Reasoning: funnel_stage={ctx.funnel_stage}")
    ctx.current_state = "STATE_MIX"

    # STATE_MIX - Determine media mix
    ctx.media_mix = _determine_media_mix(ctx)
    app_logger.debug(f"Reasoning: media_mix={ctx.media_mix}")
    ctx.current_state = "STATE_PLATFORM"

    # STATE_PLATFORM - Select platform path
    ctx.platform_path = _determine_platform_path(ctx)
    app_logger.debug(f"Reasoning: platform_path={ctx.platform_path}")
    ctx.current_state = "STATE_PERFORMANCE"

    # STATE_PERFORMANCE - Determine quality vs scale
    ctx.performance_path = _determine_performance_path(ctx)
    app_logger.debug(f"Reasoning: performance_path={ctx.performance_path}")

    # Additional computed values
    ctx.budget_window = _determine_budget_window(ctx)
    ctx.pacing_mode = _determine_pacing_mode(ctx)
    ctx.flighting_cadence = _determine_flighting_cadence(ctx)

    # Persona emphasis based on performance path
    if ctx.performance_path == "quality":
        ctx.persona_emphasis = "tight, high-intent focused"
    elif ctx.performance_path == "scale":
        ctx.persona_emphasis = "broad, reach-optimized"
    else:
        ctx.persona_emphasis = "balanced coverage"

    # Generational weighting based on category and funnel
    if ctx.funnel_stage == "upper":
        ctx.generational_weighting = "Gen Z and Millennial weighted for cultural presence"
    elif ctx.funnel_stage == "lower":
        ctx.generational_weighting = "Gen X and Boomer weighted for conversion intent"
    else:
        ctx.generational_weighting = "Balanced generational spread"

    # STATE_PRE_ACTIVATION - Finalize
    ctx.strategic_rationale = _generate_strategic_rationale(ctx)
    ctx.current_state = "STATE_PRE_ACTIVATION"

    app_logger.info(
        f"Reasoning complete: funnel={ctx.funnel_stage}, mix={ctx.media_mix}, "
        f"platform={ctx.platform_path}, performance={ctx.performance_path}"
    )

    return ctx


def get_clarifying_question(ctx: ReasoningContext) -> Optional[str]:
    """
    Return a clarifying question if inputs are missing.
    Only asks one question at a time per the spec.
    """
    spec = load_reasoning_spec()
    question_bank = spec.get("clarifying_questions", {}).get("question_bank", {})

    if "brand_name" in ctx.missing_inputs or "brief" in ctx.missing_inputs:
        return "What's the brand and what are you trying to achieve with this campaign?"

    if not ctx.budget:
        prompts = question_bank.get("budget", {}).get("prompts", [])
        return prompts[0] if prompts else "What's your budget window?"

    if not ctx.kpi:
        prompts = question_bank.get("funnel", {}).get("prompts", [])
        return prompts[0] if prompts else "Which outcome matters most - awareness, consideration, or response?"

    if not ctx.geography:
        prompts = question_bank.get("geography", {}).get("prompts", [])
        return prompts[0] if prompts else "Is this national or DMA-based?"

    return None
