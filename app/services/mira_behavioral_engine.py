"""
MIRA Behavioral Engine runtime helpers.

This module implements a thin runtime around the canonical behavioral JSON spec
(`phase_3_docs/MIRA_behavioral_engine_.json`).

Scope (v1):
- Load and cache the behavioral spec.
- Provide helpers for:
  - retrieving state configs,
  - getting the greeting message,
  - resolving simple state transitions (where the spec is explicit),
  - applying correction patterns,
  - enforcing Anchor → Frame → Offer → Move + guiding-move rules at the end of messages.

Reasoning math, Packaging, and Activation logic stay in their existing modules;
this file only concerns conversational / interaction behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.logger import app_logger


BEHAVIOR_SPEC_REL_PATH = "phase_3_docs/MIRA_behavioral_engine_.json"


@lru_cache(maxsize=1)
def load_behavior_spec() -> Dict[str, Any]:
    """
    Load the canonical MIRA behavioral engine JSON spec from disk.

    The spec is treated as immutable at runtime. If the file cannot be loaded,
    this raises a RuntimeError so callers can fail fast.
    """
    # Resolve from project root (two levels up from this file: app/services/ -> project root)
    root = Path(__file__).resolve().parents[2]
    spec_path = root / BEHAVIOR_SPEC_REL_PATH

    if not spec_path.exists():
        raise RuntimeError(f"MIRA behavioral spec not found at {spec_path}")

    try:
        import json

        with spec_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Failed to load MIRA behavioral spec: {exc}") from exc

    app_logger.info(
        "Loaded MIRA behavioral spec "
        f"(name={data.get('meta', {}).get('name')}, version={data.get('meta', {}).get('version')})"
    )
    return data


@dataclass(frozen=True)
class GuidingMoveConfig:
    """Configuration for end-of-message guidance."""

    must_end_with_guiding_move: bool
    prohibited_closings: List[str]
    default_moves: List[str]


def get_guiding_move_config() -> GuidingMoveConfig:
    """Return guiding-move configuration derived from the spec."""
    spec = load_behavior_spec()
    guidance = spec.get("guidance_rules", {}) or {}
    grammar = spec.get("behavioral_grammar", {}) or {}
    move_examples: List[str] = (grammar.get("examples") or {}).get("move") or []

    return GuidingMoveConfig(
        must_end_with_guiding_move=bool(
            guidance.get("must_end_with_guiding_move", True)
        ),
        prohibited_closings=list(guidance.get("prohibited_closings") or []),
        default_moves=move_examples,
    )


def get_state_config(state_id: str) -> Dict[str, Any]:
    """
    Return the raw config dict for a given behavioral state ID.

    Example state IDs:
    - STATE_GREETING
    - STATE_INPUT
    - STATE_CLARIFICATION
    - STATE_INTERPRETATION
    - STATE_PROGRAM_GENERATION
    - STATE_REFINEMENT
    - STATE_REASONING_BRIDGE
    - STATE_ACTIVATION
    - STATE_OPTIMIZATION
    - STATE_NEUTRAL
    - STATE_EXIT
    """
    spec = load_behavior_spec()
    states = spec.get("states") or {}
    for key, cfg in states.items():
        if isinstance(cfg, dict) and cfg.get("id") == state_id:
            return cfg
    raise KeyError(f"Unknown MIRA behavioral state id: {state_id}")


def get_initial_greeting() -> str:
    """
    Return the canonical greeting message from the GREETING state.

    Used by any chat/onboarding surface that wants MIRA's first line.
    """
    cfg = get_state_config("STATE_GREETING")
    on_enter = cfg.get("on_enter") or {}
    message = on_enter.get("message_template")
    if not message:
        # Fallback to the spec text if the JSON ever changes.
        message = (
            "Hey, I'm MIRA. Tell me the campaign you're working on and what you need to achieve."
        )
    return message


def classify_input_routing(label: str) -> str:
    """
    Given an input classification label, return the next state id from INPUT state.

    The classification itself (deciding whether input is 'complete', 'partial', etc.)
    is handled at a higher layer (e.g., by intent logic or heuristics).

    Valid labels (from spec):
    - 'complete'
    - 'partial'
    - 'unclear'
    - 'request_program'
    - 'request_activation'
    """
    spec = load_behavior_spec()
    input_state = spec.get("states", {}).get("input") or {}
    classification = input_state.get("classification") or {}
    next_state = classification.get(label)
    if not next_state:
        raise ValueError(f"Unsupported input classification label: {label}")
    return next_state


def apply_correction_pattern(kind: str) -> Optional[str]:
    """
    Return the standardized correction message for a given failure mode.

    Valid kinds (from spec):
    - 'incorrect_direction'
    - 'vague_brief'
    - 'off_scope'
    - 'invented_persona'
    - 'overload' (behavioral only; returns None as it is not a fixed sentence)
    """
    spec = load_behavior_spec()
    patterns = spec.get("correction_patterns") or {}
    pattern = patterns.get(kind)
    if not pattern:
        return None

    # Some patterns encode 'behavior' instead of a static sentence (e.g., overload)
    if "response_template" in pattern:
        return pattern["response_template"]
    return None


def enforce_guiding_move(message: str) -> str:
    """
    Ensure that a strategist-facing message ends with a guiding move,
    in line with the behavioral spec.

    - If guiding moves are disabled, return unchanged.
    - If message already ends with a prohibited closing, replace it.
    - Otherwise, append a default guiding move on a new line.
    """
    cfg = get_guiding_move_config()

    if not cfg.must_end_with_guiding_move:
        return message

    stripped = message.rstrip()
    lower = stripped.lower()

    # Remove prohibited customer-service closings if present at the tail
    for bad in cfg.prohibited_closings:
        bad_lower = bad.lower()
        if lower.endswith(bad_lower):
            # Trim the bad closing off
            without = stripped[: -len(bad)].rstrip()
            stripped = without
            lower = stripped.lower()
            break

    # Choose a default guiding move
    move = cfg.default_moves[0] if cfg.default_moves else "Say the word and I'll build it."

    # If the message already ends with one of the canonical moves, don't duplicate.
    for existing in cfg.default_moves:
        if existing and lower.endswith(existing.lower()):
            return stripped

    # Append guiding move on a new line.
    return f"{stripped}\n\n{move}"


def get_plain_language_prefix(default: str = "Here's the simple version:") -> str:
    """
    Return the preferred plain-language prefix from the spec.

    Higher layers decide WHEN to call this; this helper only surfaces the canonical text.
    """
    spec = load_behavior_spec()
    layer = spec.get("plain_language_layer") or {}
    prefixes: List[str] = layer.get("prefixes") or []
    return prefixes[0] if prefixes else default


def get_mode_definitions() -> Dict[str, Any]:
    """
    Return the full mode definition block from the spec.

    Modes:
    - trader
    - planner
    - creative
    - smb
    - founder
    """
    spec = load_behavior_spec()
    return (spec.get("modes") or {}).get("definitions") or {}


@lru_cache(maxsize=1)
def get_canonical_system_prompt() -> str:
    """
    Build the canonical MIRA system prompt from the Behavioral spec.
    This is the stable Experience/Behavior layer we prepend to all LLM calls.
    """
    spec = load_behavior_spec()

    # Tone & philosophy
    philosophy = spec.get("philosophy", {}) or {}
    grammar = spec.get("behavioral_grammar", {}) or {}
    guard = (spec.get("guardrails") or {}).get("must") or []
    guard_not = (spec.get("guardrails") or {}).get("must_not") or []
    pl = spec.get("plain_language_layer", {}) or {}
    modes = (spec.get("modes") or {}).get("definitions") or {}

    tone_lines = [
        "You are MIRA — RJM’s strategist.",
        "Tone: calm, clean, confident; short, intentional sentences; no emojis; no AI tropes; no apologies.",
        "Behavior grammar: Anchor → Frame → Offer → Move.",
        "Always end meaningful responses with a single clear next step (a guiding move).",
        "Ask at most one clarifying question per turn, only when required to move forward.",
    ]

    must_lines = [f"- {m}" for m in guard]
    must_not_lines = [f"- Do NOT {m.replace('_', ' ')}" for m in guard_not]

    mode_lines = ["Mode cues (structure may adapt; tone never changes):"]
    for name, cfg in modes.items():
        desc = cfg.get("description", "")
        mode_lines.append(f"- {name}: {desc}")

    definitions = [
        "Key definitions you may use concisely when asked:",
        "- RJM Personas: identity- and culture-based audience archetypes used to target how people actually behave and signal meaning.",
        "- Persona Program: a structured plan built from RJM Personas (personas, insights, demos, portfolio) that organizes how the brand shows up in culture and who to reach.",
        "- Activation Summary: strategist handoff for launch — platform path, budget window, pacing, flighting, persona→channel mapping, packaging notes, and why it works.",
    ]

    definitional_rule = (
        "If the user asks a general/definitional question (e.g., “What are RJM Personas?”), "
        "briefly answer in 1–3 sentences, then ask one minimal follow-up question (brand, brief, or goal) to move forward."
    )

    # Compose final prompt
    lines: List[str] = []
    lines.append("\n".join(tone_lines))
    lines.append("\nBehavioral musts:\n" + "\n".join(must_lines) if must_lines else "")
    lines.append("\nNever do:\n" + "\n".join(must_not_lines) if must_not_lines else "")
    lines.append("\n" + "\n".join(mode_lines))
    lines.append("\n" + definitional_rule)
    lines.append("\n" + "\n".join(definitions))

    return "\n".join([l for l in lines if l])


