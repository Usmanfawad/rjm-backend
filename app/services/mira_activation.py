"""
MIRA Activation helpers.

This module reads the activation JSON modules from `phase_3_docs` and exposes
helpers to assemble an Activation Summary Block for strategist handoff,
aligned with the Activation Layer spec.

This version integrates with the full Reasoning Engine to compute:
- Platform path from category, budget, timeline, and constraints
- Budget window from spend level and flight length
- Pacing mode from campaign objectives
- Flighting cadence from category and timing
- Media mix from funnel stage and category logic
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from app.config.logger import app_logger

if TYPE_CHECKING:
    from app.services.mira_reasoning_engine import ReasoningContext


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_json(relative_path: str) -> Dict[str, Any]:
    """Load a JSON file from the project root, returning empty dict on failure."""
    import json

    path = PROJECT_ROOT / relative_path
    if not path.exists():
        app_logger.warning(f"MIRA activation spec not found at {path}")
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        app_logger.error(f"Failed to load MIRA activation spec {relative_path}: {exc}")
        return {}


@lru_cache(maxsize=1)
def load_output_block_spec() -> Dict[str, Any]:
    return _load_json("phase_3_docs/mira_activation__output_blocks_module_4.txt")


@lru_cache(maxsize=1)
def load_budget_pacing_spec() -> Dict[str, Any]:
    return _load_json("phase_3_docs/mira_activation_budget_pacing_module_2.txt")


@lru_cache(maxsize=1)
def load_flighting_spec() -> Dict[str, Any]:
    return _load_json("phase_3_docs/mira_activation_flighting_module_3.txt")


@lru_cache(maxsize=1)
def load_platform_logic_spec() -> Dict[str, Any]:
    return _load_json("phase_3_docs/mira_activation_platform_logic_module_5.txt")


@lru_cache(maxsize=1)
def load_platform_path_spec() -> Dict[str, Any]:
    return _load_json("phase_3_docs/mira_activation_platform_path_module_1.txt")


@dataclass
class ActivationPlan:
    """Full activation plan surface for chat output, computed by Reasoning Engine."""

    platform_path: str
    budget_window: str
    pacing_mode: str
    flighting_cadence: str
    persona_deployment: str
    channel_deployment: str
    deal_id_or_packaging: str
    activation_rationale: str

    # Extended fields from Reasoning Engine
    funnel_stage: str = "mid"
    media_mix: Optional[Dict[str, str]] = None
    performance_path: str = "balanced"
    persona_emphasis: str = "balanced"
    generational_weighting: Optional[str] = None


@dataclass
class OptimizationSuggestion:
    """Structured downstream optimization suggestion."""

    move: str
    rationale: str
    next_step: str


def infer_platform_path(user_text: str | None = None) -> str:
    """
    Heuristic platform path, aligned with Activation spec:
    - If user mentions a DSP explicitly → "DSP"
    - Otherwise → "Direct via RJM"
    """
    txt = (user_text or "").lower()
    if any(w in txt for w in ("dsp", "dv360", "trade desk", "ttd", "amazon dsp", "yahoo")):
        return "DSP"
    return "Direct via RJM"


def default_budget_window() -> str:
    """
    Default to 'single' budget window per spec:
    - Used for steady awareness, longer flights, consistent delivery.
    """
    return "single"


def default_pacing_mode() -> str:
    """Default pacing = standard (even daily pacing)."""
    return "standard"


def default_flighting_cadence() -> str:
    """Default flighting = linear (even delivery)."""
    return "linear"


def build_activation_plan(
    brand_name: str,
    brief: str,
    category: str | None = None,
    user_text: str | None = None,
    kpi: str | None = None,
    budget: float | None = None,
    timeline: str | None = None,
    geography: str | None = None,
    creative_angle: str | None = None,
    platform_preference: str | None = None,
) -> ActivationPlan:
    """
    Construct an ActivationPlan using the full Reasoning Engine.

    This integrates with the Reasoning Engine to compute:
    - Funnel stage from category, KPI, and brief analysis
    - Media mix from funnel stage and category logic
    - Platform path from budget, timeline, and constraints
    - Budget window, pacing, and flighting from campaign parameters
    """
    from app.services.mira_reasoning_engine import run_reasoning_engine

    # Run the full Reasoning Engine
    reasoning_ctx = run_reasoning_engine(
        brand_name=brand_name,
        brief=brief,
        category=category,
        kpi=kpi,
        budget=budget,
        timeline=timeline,
        geography=geography,
        creative_angle=creative_angle,
        platform_preference=platform_preference,
        user_text=user_text,
    )

    # Build persona deployment based on funnel stage
    if reasoning_ctx.funnel_stage == "upper":
        persona_deployment = (
            "Primary personas to CTV for cultural presence; support personas to OLV and Audio for reach."
        )
    elif reasoning_ctx.funnel_stage == "lower":
        persona_deployment = (
            "Primary personas to OLV and Display for conversion; support personas to Audio for frequency."
        )
    else:  # mid funnel
        persona_deployment = (
            "Primary personas to CTV and OLV; support personas to Audio and Display."
        )

    # Build channel deployment based on media mix
    # NOTE: Using strategic descriptions instead of specific percentages
    # The actual percentages are computed dynamically and available in reasoning_ctx.media_mix
    mix = reasoning_ctx.media_mix

    # Build strategic channel deployment without reciting percentages
    channel_descriptions = []
    if "CTV" in mix:
        channel_descriptions.append("CTV as the cultural anchor for storytelling and emotional connection")
    if "OLV" in mix:
        channel_descriptions.append("OLV for brand reinforcement and consideration")
    if "Audio" in mix:
        channel_descriptions.append("Audio for ritual moments and frequency")
    if "Display" in mix:
        channel_descriptions.append("Display for precision targeting and conversion support")

    channel_deployment = "; ".join(channel_descriptions) + "."

    # Build deal/packaging description
    if reasoning_ctx.platform_path == "DSP":
        deal_id_or_packaging = "Generate DSP-ready deal IDs or PMPs for the selected personas."
    elif reasoning_ctx.platform_path == "Hybrid":
        deal_id_or_packaging = (
            "Package as a Hybrid activation: Direct via RJM for premium CTV inventory, "
            "DSP for scale across OLV/Display."
        )
    else:
        deal_id_or_packaging = "Package as a Direct via RJM activation with RJM-managed pacing and QA."

    # Use the strategic rationale from Reasoning Engine
    activation_rationale = reasoning_ctx.strategic_rationale

    app_logger.info(
        "MIRA activation plan assembled via Reasoning Engine",
        extra={
            "brand": brand_name,
            "category": reasoning_ctx.category,
            "funnel_stage": reasoning_ctx.funnel_stage,
            "platform_path": reasoning_ctx.platform_path,
            "budget_window": reasoning_ctx.budget_window,
            "pacing_mode": reasoning_ctx.pacing_mode,
            "flighting_cadence": reasoning_ctx.flighting_cadence,
            "performance_path": reasoning_ctx.performance_path,
        },
    )

    return ActivationPlan(
        platform_path=reasoning_ctx.platform_path,
        budget_window=reasoning_ctx.budget_window,
        pacing_mode=reasoning_ctx.pacing_mode,
        flighting_cadence=reasoning_ctx.flighting_cadence,
        persona_deployment=persona_deployment,
        channel_deployment=channel_deployment,
        deal_id_or_packaging=deal_id_or_packaging,
        activation_rationale=activation_rationale,
        # Store additional reasoning context
        funnel_stage=reasoning_ctx.funnel_stage,
        media_mix=reasoning_ctx.media_mix,
        performance_path=reasoning_ctx.performance_path,
        persona_emphasis=reasoning_ctx.persona_emphasis,
        generational_weighting=reasoning_ctx.generational_weighting,
    )


def format_activation_summary_block(plan: ActivationPlan, include_reasoning: bool = False) -> str:
    """
    Render a multi-line Campaign Activation Summary block, aligned with
    the Activation Layer spec.

    Args:
        plan: The ActivationPlan to format
        include_reasoning: If True, include funnel/mix/performance details
    """
    lines: list[str] = []
    lines.append("Campaign Activation Summary")
    lines.append(f"• Platform Path: {plan.platform_path}")
    lines.append(f"• Budget Window: {plan.budget_window.capitalize()}")
    lines.append(f"• Pacing: {plan.pacing_mode.capitalize()}")
    lines.append(f"• Flighting: {plan.flighting_cadence.capitalize()}")
    lines.append(f"• Persona Deployment: {plan.persona_deployment}")
    lines.append(f"• Channel Deployment: {plan.channel_deployment}")
    lines.append(f"• Packaging: {plan.deal_id_or_packaging}")

    if include_reasoning:
        lines.append("")
        lines.append("Reasoning Context:")
        lines.append(f"• Funnel Stage: {plan.funnel_stage.capitalize()}")
        if plan.media_mix:
            mix_str = ", ".join(f"{k}: {v}" for k, v in plan.media_mix.items())
            lines.append(f"• Media Mix: {mix_str}")
        lines.append(f"• Performance Path: {plan.performance_path.capitalize()}")
        lines.append(f"• Persona Emphasis: {plan.persona_emphasis}")
        if plan.generational_weighting:
            lines.append(f"• Generational Weighting: {plan.generational_weighting}")

    lines.append("")
    lines.append(f"• Why it works: {plan.activation_rationale}")
    return "\n".join(lines)


def _downstream_spec() -> Dict[str, Any]:
    """Return the downstream_optimization section from the activation spec."""
    spec = load_output_block_spec()
    return spec.get("downstream_optimization") or {}


def suggest_downstream_optimization(user_text: str) -> OptimizationSuggestion:
    """
    Plan a mini optimization suggestion using downstream_optimization rules:
    - 1 move
    - 1 rationale
    - 1 next step
    """
    text = (user_text or "").lower()

    if any(phrase in text for phrase in ("more scale", "need more scale", "more reach", "bigger reach")):
        return OptimizationSuggestion(
            move="Widen persona emphasis slightly and push a bit more weight into OLV and Display.",
            rationale=(
                "Widening personas and leaning on OLV/Display opens up additional volume without breaking the RJM structure."
            ),
            next_step=(
                "Ask your team to loosen persona filters one notch and increase OLV/Display share inside the mix."
            ),
        )
    if any(phrase in text for phrase in ("higher quality", "better quality", "too broad", "tighten up")):
        return OptimizationSuggestion(
            move="Tighten persona emphasis and tilt toward higher-intent personas inside the existing program.",
            rationale=(
                "Focusing on the highest-intent personas improves quality without changing the underlying packaging logic."
            ),
            next_step=(
                "Have ops prioritize the top-intent personas from this program and reduce spend on the broadest ones."
            ),
        )
    if any(phrase in text for phrase in ("under-delivery", "underdelivering", "not delivering", "too slow")):
        return OptimizationSuggestion(
            move="Shift some budget from CTV into OLV and add Display support to help the campaign clear delivery.",
            rationale=(
                "OLV and Display absorb spend more efficiently, keeping the cultural frame while fixing under-delivery."
            ),
            next_step=(
                "Rebalance the mix toward OLV and Display for the next flight while keeping CTV as the cultural anchor."
            ),
        )
    if any(phrase in text for phrase in ("over-frequency", "too much frequency", "seeing ads too often")):
        return OptimizationSuggestion(
            move="Ease off the tightest personas and spread budget a bit wider across the portfolio.",
            rationale=(
                "Easing persona tightness reduces frequency pressure without abandoning the core audience logic."
            ),
            next_step=(
                "Ask ops to relax persona filters and monitor frequency on CTV while using OLV/Display to carry volume."
            ),
        )
    if any(phrase in text for phrase in ("weak markets", "some dmas", "some markets", "geo")):
        return OptimizationSuggestion(
            move="Increase DMA weighting where you’re seeing signal and let weaker markets run lighter.",
            rationale=(
                "Turning up weight in the right DMAs respects local culture and improves efficiency without rewriting the plan."
            ),
            next_step="Identify the top-performing DMAs and increase weight there for the next optimization window.",
        )

    # Default behavior when no specific pattern is detected
    return OptimizationSuggestion(
        move=(
            "Shift persona emphasis slightly toward higher-intent segments while adding a bit more OLV for scale."
        ),
        rationale="This keeps the program grounded in identity while giving you more room to move on performance.",
        next_step=(
            "Have ops rebalance toward higher-intent personas and increase OLV share by a small margin this flight."
        ),
    )




