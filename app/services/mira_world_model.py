"""
MIRA World Model Integration.

This module loads and provides access to all World Model JSON specs from phase_3_docs:
- Reasoning State Machine (decision trees)
- Category-Funnel-Channel Mesh
- Cross-Domain Reasoning Maps
- Agent Identity
- Behavior Domain
- Mode Definitions

All reasoning and activation decisions are driven by these specs, not hardcoded Python logic.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.logger import app_logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE_3_DOCS = PROJECT_ROOT / "phase_3_docs"


def _load_json(relative_path: str) -> Dict[str, Any]:
    """Load a JSON file from phase_3_docs, returning empty dict on failure."""
    path = PHASE_3_DOCS / relative_path
    if not path.exists():
        app_logger.warning(f"World Model spec not found: {path}")
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        app_logger.error(f"Failed to load World Model spec {relative_path}: {exc}")
        return {}


# ════════════════════════════════════════════════════════════════════════════
# REASONING STATE MACHINE
# ════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def load_reasoning_state_machine() -> Dict[str, Any]:
    """Load the full Reasoning State Machine JSON spec."""
    return _load_json("deliverables/3_REASONING_STATE_MACHINE.json")


def get_reasoning_loop() -> List[Dict[str, Any]]:
    """Get the canonical reasoning loop steps."""
    spec = load_reasoning_state_machine()
    return spec.get("reasoning_loop", {}).get("steps", [])


def get_category_profile(category: str) -> Dict[str, Any]:
    """Get category-specific profile from the decision trees."""
    spec = load_reasoning_state_machine()
    trees = spec.get("decision_trees", {})
    category_tree = trees.get("tree_0_category_logic", {})
    profiles = category_tree.get("category_profiles", {})
    
    # Try exact match first, then case-insensitive
    if category in profiles:
        return profiles[category]
    
    category_lower = category.lower()
    for key, profile in profiles.items():
        if key.lower() == category_lower:
            return profile
    
    return {}


def get_mix_template(funnel_stage: str) -> Dict[str, str]:
    """Get media mix template for a funnel stage."""
    spec = load_reasoning_state_machine()
    trees = spec.get("decision_trees", {})
    mix_tree = trees.get("tree_c_media_mix", {})
    templates = mix_tree.get("mix_templates", {})
    
    funnel_map = {
        "upper": "upper_funnel_emotional",
        "mid": "mid_funnel_balanced",
        "lower": "lower_funnel_performance",
    }
    
    template_key = funnel_map.get(funnel_stage, "mid_funnel_balanced")
    return templates.get(template_key, {
        "CTV": "35-45%",
        "OLV": "30-35%",
        "Audio": "15-20%",
        "Display": "10-15%"
    })


def get_creative_angle_modifiers() -> Dict[str, Dict[str, str]]:
    """Get creative angle modifiers for mix adjustment."""
    spec = load_reasoning_state_machine()
    trees = spec.get("decision_trees", {})
    mix_tree = trees.get("tree_c_media_mix", {})
    return mix_tree.get("creative_angle_modifiers", {})


def get_budget_rules() -> Dict[str, Any]:
    """Get budget window decision rules."""
    spec = load_reasoning_state_machine()
    trees = spec.get("decision_trees", {})
    budget_tree = trees.get("tree_a_budget_window", {})
    return budget_tree.get("rules", {})


def get_platform_decision_flow() -> List[Dict[str, Any]]:
    """Get platform path decision flow."""
    spec = load_reasoning_state_machine()
    trees = spec.get("decision_trees", {})
    platform_tree = trees.get("tree_b_dsp_vs_direct", {})
    return platform_tree.get("decision_flow", [])


def get_kpi_buckets() -> Dict[str, List[str]]:
    """Get KPI to funnel mapping."""
    spec = load_reasoning_state_machine()
    states = spec.get("reasoning_states", {})
    performance = states.get("performance", {})
    return performance.get("kpi_buckets", {
        "upper_funnel": ["reach", "video_completion_rate", "view_through"],
        "mid_funnel": ["site_visits", "qualified_traffic", "engagement"],
        "lower_funnel": ["conversion", "foot_traffic", "CPA_outcomes"]
    })


def get_clarifying_question(topic: str) -> Optional[str]:
    """Get a clarifying question from the question bank."""
    spec = load_reasoning_state_machine()
    question_bank = spec.get("clarifying_questions", {}).get("question_bank", {})
    topic_questions = question_bank.get(topic, {})
    prompts = topic_questions.get("prompts", [])
    return prompts[0] if prompts else None


# ════════════════════════════════════════════════════════════════════════════
# CATEGORY-FUNNEL-CHANNEL MESH
# ════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def load_category_funnel_mesh() -> Dict[str, Any]:
    """Load the Category-Funnel-Channel Mesh spec."""
    return _load_json("MIRA WORLD SUPERVISORY/category_funnel_channel_mesh.json")


def get_funnel_channels(funnel_stage: str) -> List[str]:
    """Get recommended channels for a funnel stage."""
    mesh = load_category_funnel_mesh()
    rules = mesh.get("mesh_rules", {})
    
    funnel_map = {
        "upper": "upper_funnel_categories",
        "mid": "mid_funnel_categories",
        "lower": "lower_funnel_categories",
    }
    
    key = funnel_map.get(funnel_stage, "mid_funnel_categories")
    return rules.get(key, {}).get("channels", ["CTV", "OLV"])


def get_identity_forward_categories() -> List[str]:
    """Get categories that are identity-forward (emotional/aspirational)."""
    mesh = load_category_funnel_mesh()
    return mesh.get("identity_mapping", {}).get("identity_forward_categories", [])


def get_utility_forward_categories() -> List[str]:
    """Get categories that are utility-forward (functional)."""
    mesh = load_category_funnel_mesh()
    return mesh.get("identity_mapping", {}).get("utility_forward_categories", [])


# ════════════════════════════════════════════════════════════════════════════
# CROSS-DOMAIN REASONING MAPS
# ════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def load_cross_domain_maps() -> Dict[str, Any]:
    """Load the Cross-Domain Reasoning Maps spec."""
    return _load_json("MIRA WORLD SUPERVISORY/cross_domain_reasoning_maps.json")


def get_category_funnel_bias(category: str) -> str:
    """Get the funnel bias for a category from cross-domain maps."""
    maps = load_cross_domain_maps()
    category_funnel = maps.get("matrices", {}).get("category_funnel_map", {})
    return category_funnel.get(category.lower(), "mid")


def get_category_channels(category: str) -> List[str]:
    """Get recommended channels for a category."""
    maps = load_cross_domain_maps()
    category_channel = maps.get("matrices", {}).get("category_channel_map", {})
    return category_channel.get(category.lower(), ["CTV", "OLV"])


def get_identity_signals() -> List[str]:
    """Get all identity signals."""
    maps = load_cross_domain_maps()
    return maps.get("matrices", {}).get("identity_category_map", {}).get("identity_signals", [])


def get_tension_behaviors(tension: str) -> List[str]:
    """Get behaviors associated with a tension state."""
    maps = load_cross_domain_maps()
    tension_map = maps.get("matrices", {}).get("behavior_tension_map", {})
    return tension_map.get(tension, [])


# ════════════════════════════════════════════════════════════════════════════
# AGENT IDENTITY
# ════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def load_agent_identity() -> Dict[str, Any]:
    """Load MIRA's agent identity spec."""
    return _load_json("MIRA WORLD SUPERVISORY/mira_agent_identity.json")


def get_mira_posture() -> str:
    """Get MIRA's interpretive posture."""
    identity = load_agent_identity()
    return identity.get("agent_identity", {}).get(
        "posture", 
        "identity-first, tension-governed, culturally grounded"
    )


def get_mira_boundaries() -> List[str]:
    """Get what MIRA does not do."""
    identity = load_agent_identity()
    return identity.get("boundaries", {}).get("does_not_do", [])


def get_interpretation_principles() -> Dict[str, str]:
    """Get MIRA's interpretation principles."""
    identity = load_agent_identity()
    return identity.get("interpretation_principles", {})


# ════════════════════════════════════════════════════════════════════════════
# BEHAVIOR DOMAIN
# ════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def load_behavior_domain() -> Dict[str, Any]:
    """Load the Behavior Domain spec."""
    return _load_json("MIRA WORLD DOMAIN/behavior_domain.json")


def get_behavior_modes() -> List[str]:
    """Get all behavior modes."""
    domain = load_behavior_domain()
    components = domain.get("behavior_components", {})
    modes = components.get("behavior_modes", {})
    return modes.get("modes", [])


def get_tension_to_behaviors() -> List[Dict[str, Any]]:
    """Get tension-to-behavior mappings."""
    domain = load_behavior_domain()
    return domain.get("tension_to_behavior_mapping", {}).get("tension_driven_behaviors", [])


def get_behavior_drivers() -> List[str]:
    """Get behavior drivers (internal identity pressures)."""
    domain = load_behavior_domain()
    components = domain.get("behavior_components", {})
    drivers = components.get("behavior_drivers", {})
    return drivers.get("drivers", [])


# ════════════════════════════════════════════════════════════════════════════
# MODE DEFINITIONS (Enhanced from Behavioral Engine)
# ════════════════════════════════════════════════════════════════════════════

# Full mode definitions with detailed styling
MODE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "trader": {
        "description": "Media buyer focused on CPMs, deal IDs, DSP operations",
        "styling": {
            "sentence_length": "short",
            "lexical_density": "high",
            "verbosity": "low",
            "cultural_framing": False,
            "narrative_emphasis": False,
        },
        "tone_instructions": (
            "Keep responses tight and operational. "
            "Use DSP terminology freely. "
            "No extra explanation layers. "
            "Trust their programmatic fluency."
        ),
        "response_suffix": None,
    },
    "planner": {
        "description": "Strategist focused on culture, identity, tensions, insights",
        "styling": {
            "sentence_length": "medium",
            "lexical_density": "medium",
            "verbosity": "medium",
            "cultural_framing": True,
            "narrative_emphasis": False,
        },
        "tone_instructions": (
            "Add cultural and strategic framing. "
            "Emphasize tensions and insights. "
            "Connect personas to how audiences signal identity and meaning. "
            "Use strategic language without jargon."
        ),
        "response_suffix": (
            "This approach is grounded in cultural insight and behavioral tensions, "
            "not just demographic reach. The personas connect to how your audience "
            "actually signals identity and meaning."
        ),
    },
    "creative": {
        "description": "Agency creative focused on narrative, storytelling, brand voice",
        "styling": {
            "sentence_length": "medium_long",
            "lexical_density": "medium",
            "verbosity": "medium_high",
            "cultural_framing": True,
            "narrative_emphasis": True,
        },
        "tone_instructions": (
            "Emphasize narrative and brand expression. "
            "Connect personas to storytelling opportunities. "
            "Highlight emotional centers and tensions that creative can build around. "
            "Lean into the human center of each segment."
        ),
        "response_suffix": (
            "The persona structure gives your creative a clear human center to write toward. "
            "Each segment carries distinct tension and motivation you can build narrative around."
        ),
    },
    "smb": {
        "description": "Small business owner, needs simple language and clear direction",
        "styling": {
            "sentence_length": "short",
            "lexical_density": "low",
            "verbosity": "medium",
            "cultural_framing": False,
            "narrative_emphasis": False,
        },
        "tone_instructions": (
            "Use plain language. Avoid marketing jargon. "
            "Be direct and actionable. "
            "Explain what things mean in simple terms. "
            "Focus on what they should actually do."
        ),
        "response_suffix": (
            "Here's the simple version: "
            "You can think of this as a clean, ready-to-run plan for who to reach and where to show up."
        ),
    },
    "founder": {
        "description": "Startup founder focused on growth, scale, efficiency",
        "styling": {
            "sentence_length": "medium",
            "lexical_density": "high",
            "verbosity": "medium",
            "cultural_framing": False,
            "narrative_emphasis": False,
        },
        "tone_instructions": (
            "Emphasize efficiency, growth, and ROI. "
            "Focus on capital efficiency and CAC. "
            "Show how the structure scales with budget. "
            "Use startup/growth terminology."
        ),
        "response_suffix": (
            "This setup is designed for capital efficiency — reaching the right people without waste. "
            "The structure scales with you as budget grows, keeping CAC tight."
        ),
    },
}


def get_mode_definition(mode: str) -> Dict[str, Any]:
    """Get the full mode definition including tone instructions."""
    return MODE_DEFINITIONS.get(mode, {})


def get_mode_tone_instructions(mode: str) -> str:
    """Get tone instructions for a specific mode."""
    definition = get_mode_definition(mode)
    return definition.get("tone_instructions", "")


def get_mode_response_suffix(mode: str) -> Optional[str]:
    """Get the response suffix for a mode (if any)."""
    definition = get_mode_definition(mode)
    return definition.get("response_suffix")


def get_mode_styling(mode: str) -> Dict[str, Any]:
    """Get styling parameters for a mode."""
    definition = get_mode_definition(mode)
    return definition.get("styling", {})


# ════════════════════════════════════════════════════════════════════════════
# WORLD MODEL SUMMARY
# ════════════════════════════════════════════════════════════════════════════

def get_world_model_context(category: str, funnel_stage: str, mode: str | None = None) -> str:
    """
    Build a comprehensive World Model context string for LLM prompts.
    
    This gives the LLM the full context from the World Model to make
    identity-first, tension-governed decisions.
    """
    parts = []
    
    # Agent identity
    posture = get_mira_posture()
    parts.append(f"MIRA's posture: {posture}")
    
    # Category profile
    profile = get_category_profile(category)
    if profile:
        parts.append(f"\nCategory Profile ({category}):")
        parts.append(f"- Mix bias: {profile.get('mix_bias', 'balanced')}")
        parts.append(f"- Funnel bias: {profile.get('funnel_bias', 'mid')}")
        parts.append(f"- Behavioral tension: {profile.get('behavioral_tension', profile.get('tension', 'varied'))}")
    
    # Funnel context
    mix_template = get_mix_template(funnel_stage)
    parts.append(f"\nFunnel Stage: {funnel_stage}")
    parts.append(f"Recommended Mix: {mix_template}")
    
    # Mode context
    if mode:
        mode_def = get_mode_definition(mode)
        if mode_def:
            parts.append(f"\nMode: {mode} - {mode_def.get('description', '')}")
            parts.append(f"Tone: {mode_def.get('tone_instructions', '')}")
    
    # Interpretation principles
    principles = get_interpretation_principles()
    if principles:
        parts.append("\nInterpretation Principles:")
        for key, value in principles.items():
            parts.append(f"- {key}: {value}")
    
    return "\n".join(parts)


# Initialize and log
app_logger.info(
    "MIRA World Model loaded",
    extra={
        "reasoning_spec": bool(load_reasoning_state_machine()),
        "category_mesh": bool(load_category_funnel_mesh()),
        "cross_domain_maps": bool(load_cross_domain_maps()),
        "agent_identity": bool(load_agent_identity()),
        "behavior_domain": bool(load_behavior_domain()),
    }
)

