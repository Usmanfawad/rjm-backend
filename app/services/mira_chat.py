"""
MIRA chat orchestration layer.

This module wires the Behavioral Engine spec into a simple, stateless chat turn
handler that the FastAPI layer can call.

Design (v1):
- Stateless: the client sends the current behavioral `state` and message history.
- We interpret the state, apply the behavioral rules, and return:
  - a strategist-style reply, and
  - the next behavioral state id.

This version focuses on:
- GREETING → INPUT → (optional) CLARIFICATION → PROGRAM GENERATION
- Bridging into Reasoning/Activation as placeholders to be expanded later.
"""

from __future__ import annotations

import json
from typing import List, Tuple, Optional
from uuid import UUID

from app.api.rjm.schemas import (
    ChatMessage,
    GenerateProgramRequest,
    MiraChatRequest,
    MiraChatResponse,
)
from app.config.logger import app_logger
from app.config.settings import settings
from app.services.mira_behavioral_engine import (
    apply_correction_pattern,
    classify_input_routing,
    get_initial_greeting,
)
from app.services.mira_behavioral_engine import get_plain_language_prefix, get_canonical_system_prompt
from app.services.mira_activation import build_activation_plan
from app.services.rjm_rag import generate_program_with_rag
from app.services.rjm_vector_store import get_openai_client
from app.services.mira_session import (
    get_session,
    update_session,
    add_message_to_history,
    get_conversation_history,
    set_program_summary,
    get_program_summary,
)


# In-memory storage for pending persona generations to be saved
# Maps session_id -> (user_id, generation_data)
_pending_generations: dict = {}


GREETING_STATE = "STATE_GREETING"
INPUT_STATE = "STATE_INPUT"


def _build_mode_aware_system_context(mode: str | None, session=None) -> str:
    """
    Build mode-aware system context from World Model.
    
    This enriches the LLM prompt with mode-specific tone instructions
    and World Model context to produce more contextually appropriate responses.
    """
    from app.services.mira_world_model import (
        get_mode_tone_instructions,
        get_mira_posture,
        get_interpretation_principles,
    )
    
    parts = []
    
    # Base posture from World Model
    posture = get_mira_posture()
    parts.append(f"MIRA's posture: {posture}")
    
    # Mode-specific tone instructions
    if mode:
        tone_instructions = get_mode_tone_instructions(mode)
        if tone_instructions:
            parts.append(f"\nMode: {mode.upper()}")
            parts.append(f"Tone instructions: {tone_instructions}")
    
    # Interpretation principles
    principles = get_interpretation_principles()
    if principles:
        parts.append("\nCore interpretation principles:")
        for key, value in list(principles.items())[:3]:  # Top 3 for conciseness
            parts.append(f"- {key}: {value}")
    
    return "\n".join(parts)
CLARIFICATION_STATE = "STATE_CLARIFICATION"
PROGRAM_GENERATION_STATE = "STATE_PROGRAM_GENERATION"
REASONING_BRIDGE_STATE = "STATE_REASONING_BRIDGE"
ACTIVATION_STATE = "STATE_ACTIVATION"
EXIT_STATE = "STATE_EXIT"
OPTIMIZATION_STATE = "STATE_OPTIMIZATION"


def _get_last_user_message(messages: List[ChatMessage]) -> str:
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content
    return ""


def _build_conversation_context(session_id: str, program_summary: str | None = None) -> str:
    """
    Build a conversation context string from session history for LLM prompts.

    Includes:
    - Previous 2-3 conversation turns (user + assistant messages)
    - Generated program summary if available

    Returns a formatted string to include in prompts.
    """
    context_parts = []

    # Get conversation history
    history = get_conversation_history(session_id)
    if history:
        context_parts.append("PREVIOUS CONVERSATION:")
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "MIRA"
            # Truncate long messages for context
            content = msg["content"]
            if len(content) > 300:
                content = content[:300] + "..."
            context_parts.append(f"{role_label}: {content}")
        context_parts.append("")

    # Include program summary if available
    if program_summary:
        context_parts.append("GENERATED PROGRAM SUMMARY:")
        context_parts.append(program_summary)
        context_parts.append("")

    return "\n".join(context_parts) if context_parts else ""


def _detect_user_intent_llm(
    user_text: str,
    conversation_context: str,
    current_state: str,
    last_mira_message: str | None = None,
) -> str:
    """
    Use LLM to detect the primary intent of the user's message with full context.

    Returns one of:
    - 'gratitude_exit': User is thanking and ending the conversation
    - 'acceptance': User is accepting/approving the plan and ready to proceed
    - 'continuation': User says "yes" or agrees to continue on the current topic
    - 'activation_request': User wants to map/see activation details
    - 'question': User is asking a question that needs an answer
    - 'optimization': User wants to adjust scale, quality, delivery, etc.
    - 'refinement': User wants to refine or change something in the program
    - 'new_topic': User is introducing new information or changing subject
    - 'general': General conversational input
    """
    # Quick pre-check for patterns to avoid LLM misclassification
    text_lower = (user_text or "").lower().strip()
    
    # PRIORITY 1: Check for explicit requests/questions first
    # These should NEVER be classified as gratitude/acceptance even with positive language
    request_indicators = (
        "can you", "could you", "please", "map out", "show me", "tell me",
        "explain", "what if", "how about", "activate", "activation plan",
        "channels", "what are", "what exactly", "want to know",
    )
    has_explicit_request = any(req in text_lower for req in request_indicators)
    has_question_mark = "?" in user_text
    
    # If there's an explicit request or question, let LLM handle it (don't short-circuit to gratitude)
    if has_explicit_request or has_question_mark:
        # Skip gratitude pre-check, let LLM classify properly
        pass
    else:
        # PRIORITY 2: Gratitude/exit patterns (only if no explicit request)
        gratitude_indicators = (
            "thank you", "thanks", "thx", "no i think", "i'm good", "im good",
            "that's all", "thats all", "i'm done", "im done", "no more",
            "that's fine", "thats fine", "we're done", "were done", "goodbye",
            "bye", "no thanks", "nope i'm good", "nope im good", "all good",
            "i think i'm good", "i think im good", "good for now",
        )
        if any(indicator in text_lower for indicator in gratitude_indicators):
            app_logger.info(f"Intent pre-check: GRATITUDE_EXIT for '{user_text[:40]}...'")
            return "gratitude_exit"
    
    client = get_openai_client()
    
    system_content = """You are an intent classifier for MIRA, a marketing AI assistant.

CLASSIFY the user's message into ONE of these categories:

PRIORITY ORDER (check these first):
1. ACTIVATION_REQUEST - User wants to see/map activation: "map out", "activation plan", "show channels", "can you activate"
2. QUESTION - User asks something: contains "?", "what is", "what are", "how does", "explain", "can you tell me"
3. OPTIMIZATION - User wants adjustments: "more scale", "more reach", "better quality", "what if"

SECONDARY (only if no request above):
- ACCEPTANCE - User approves WITHOUT any request: "looks good!", "ship it", "run it", "perfect" (and nothing more)
- GRATITUDE_EXIT - User is done/ending: "thank you", "thanks", "I'm good", "that's all", "no more" (without new requests)
- CONTINUATION - User agrees to continue: "yes", "sure", "yeah" (short affirmation only)
- REFINEMENT - User wants changes: "change", "modify", "different"
- NEW_TOPIC - User introduces new business/campaign info
- GENERAL - Everything else

CRITICAL: If the message contains BOTH positive language AND a request (like "This looks great! Can you map the activation?"), 
classify it by the REQUEST, not the positive language. Action requests take priority.

Reply with ONLY the category name, nothing else."""

    user_content = f"""MIRA's last message: "{(last_mira_message or '')[:200]}"

User says: "{user_text}"

Category:"""

    try:
        completion = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=0,
            max_tokens=15,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
        )
        raw_intent = (completion.choices[0].message.content or "").strip()
        
        # Clean up the response - extract just the intent label
        intent = raw_intent.upper().replace("_", "").replace(" ", "")
        
        # Map various formats to canonical intents
        intent_mapping = {
            "GRATITUDEEXIT": "gratitude_exit",
            "GRATITUDE_EXIT": "gratitude_exit",
            "GRATITUDE": "gratitude_exit",
            "EXIT": "gratitude_exit",
            "ACCEPTANCE": "acceptance",
            "ACCEPT": "acceptance",
            "CONTINUATION": "continuation",
            "CONTINUE": "continuation",
            "ACTIVATIONREQUEST": "activation_request",
            "ACTIVATION_REQUEST": "activation_request",
            "ACTIVATION": "activation_request",
            "QUESTION": "question",
            "OPTIMIZATION": "optimization",
            "OPTIMIZE": "optimization",
            "REFINEMENT": "refinement",
            "REFINE": "refinement",
            "NEWTOPIC": "new_topic",
            "NEW_TOPIC": "new_topic",
            "GENERAL": "general",
        }
        
        # Try to find a matching intent
        result = intent_mapping.get(intent)
        if not result:
            # Try partial matching
            for key, value in intent_mapping.items():
                if key in intent or intent in key:
                    result = value
                    break
        
        if not result:
            result = "general"
        
        app_logger.info(f"LLM intent: '{user_text[:40]}...' → raw='{raw_intent}' → {result}")
        return result
        
    except Exception as exc:
        app_logger.warning(f"LLM intent detection failed, using fallback: {exc}")
        return _detect_user_intent_fallback(user_text)


def _detect_user_intent_fallback(user_text: str) -> str:
    """
    Fallback hardcoded intent detection (used if LLM fails).
    """
    text = (user_text or "").lower().strip()

    # Gratitude/exit patterns (highest priority)
    gratitude_patterns = (
        "thank you", "thanks", "thx", "that's all", "thats all",
        "i'm done", "im done", "no more", "nothing else", "that's fine",
        "thats fine", "i'm good", "im good", "no thanks", "nope",
        "that's it", "thats it", "we're done", "were done",
    )
    if any(pattern in text for pattern in gratitude_patterns):
        return "gratitude_exit"

    # Check for questions
    if text.endswith("?") or any(p in text for p in ("what is", "what are", "how does", "how do", "can you explain", "tell me about")):
        return "question"

    # Acceptance patterns
    acceptance_patterns = (
        "looks good", "sounds good", "sounds great", "looks great",
        "run it", "ship it", "go ahead", "let's proceed", "approved",
        "perfect", "awesome", "excellent", "that works",
    )
    if any(pattern in text for pattern in acceptance_patterns):
        return "acceptance"

    # Simple yes/continuation (context-dependent, but fallback assumes continuation)
    if text in ("yes", "yeah", "yep", "sure", "ok", "okay", "yes please"):
        return "continuation"

    # Activation patterns
    if any(p in text for p in ("activate", "activation", "channels", "media plan", "launch")):
        return "activation_request"

    # Optimization patterns
    if any(p in text for p in ("more scale", "more reach", "quality", "right people")):
        return "optimization"

    return "general"


def _detect_mode(user_text: str) -> str | None:
    """
    Lightweight mode detection based on user language.
    Returns one of: 'trader', 'planner', 'creative', 'smb', 'founder', or None.

    Mode definitions from Behavioral Spec:
    - Trader: Media buyer focused on CPMs, deal IDs, DSP operations
    - Planner: Strategist focused on culture, identity, tensions, insights
    - Creative: Agency creative focused on narrative, storytelling, brand voice
    - SMB: Small business owner, needs simple language and clear direction
    - Founder: Startup founder, focused on growth, scale, efficiency
    """
    text = (user_text or "").lower()

    # Trader mode: DSP/media buying terminology
    trader_keywords = (
        "cpm", "line item", "line-item", "ttd", "dv360", "deal id", "deal-id",
        "pmp", "bid", "impressions", "trafficking", "dsp", "supply", "inventory",
        "programmatic", "bid floor", "win rate"
    )
    if any(word in text for word in trader_keywords):
        return "trader"

    # SMB mode: small business indicators
    smb_keywords = (
        "small business", "my shop", "my restaurant", "my store", "local business",
        "my bakery", "my salon", "my gym", "my practice", "small budget", "just starting"
    )
    if any(phrase in text for phrase in smb_keywords):
        return "smb"

    # Founder mode: startup/founder language
    founder_keywords = (
        "founder", "my company", "startup", "my startup", "series a", "series b",
        "seed round", "investor", "growth stage", "scale fast", "runway", "burn rate"
    )
    if any(phrase in text for phrase in founder_keywords):
        return "founder"

    # Planner mode: strategic/cultural language
    planner_keywords = (
        "tension", "culture", "identity", "insight", "consumer behavior",
        "audience insight", "cultural moment", "target audience", "segmentation",
        "brand positioning", "market analysis", "competitive", "white space"
    )
    if any(phrase in text for phrase in planner_keywords):
        return "planner"

    # Creative mode: narrative/storytelling language
    creative_keywords = (
        "narrative", "storytelling", "brand voice", "creative direction", "campaign idea",
        "concept", "tagline", "messaging", "copy", "visual", "tone of voice", "brand story",
        "emotional", "hero spot", "manifesto"
    )
    if any(phrase in text for phrase in creative_keywords):
        return "creative"

    return None


def _apply_mode_styling(base_reply: str, mode: str | None) -> str:
    """
    Apply mode-aware tweaks from World Model without breaking tone canon.

    Mode behaviors are now loaded from World Model (mira_world_model.py):
    - Trader: Keep tight, no extra layers, trust DSP fluency
    - Planner: Add cultural/strategic framing, emphasize tensions and insights
    - Creative: Add narrative emphasis, lean into storytelling and brand voice
    - SMB: Add plain-language explanation, keep it simple and actionable
    - Founder: Add efficiency/growth framing, focus on scale and ROI
    """
    from app.services.mira_world_model import get_mode_response_suffix
    
    if not mode:
        return base_reply

    # Get mode-specific suffix from World Model
    suffix = get_mode_response_suffix(mode)
    
    if mode == "trader":
        # Trader mode: tight, operational, no extra explanation
        # Trust they understand DSP terminology (no suffix)
        return base_reply

    if mode == "smb":
        # SMB mode: add plain-language explanation from World Model
        if suffix:
            return f"{base_reply}\n\n{suffix}"
        else:
            prefix = get_plain_language_prefix()
            simple_line = (
                "You can think of this as a clean, ready-to-run plan for who to reach and where to show up."
            )
            return f"{base_reply}\n\n{prefix} {simple_line}"

    if mode == "planner":
        # Planner mode: add cultural/strategic framing from World Model
        if suffix:
            return f"{base_reply}\n\n{suffix}"
        else:
            planner_frame = (
                "This approach is grounded in cultural insight and behavioral tensions, "
                "not just demographic reach. The personas connect to how your audience "
                "actually signals identity and meaning."
            )
            return f"{base_reply}\n\n{planner_frame}"

    if mode == "creative":
        # Creative mode: emphasize narrative and brand expression from World Model
        if suffix:
            return f"{base_reply}\n\n{suffix}"
        else:
            creative_frame = (
                "The persona structure gives your creative a clear human center to write toward. "
                "Each segment carries distinct tension and motivation you can build narrative around."
            )
            return f"{base_reply}\n\n{creative_frame}"

    if mode == "founder":
        # Founder mode: emphasize efficiency, growth, and ROI from World Model
        if suffix:
            return f"{base_reply}\n\n{suffix}"
        else:
            founder_frame = (
                "This setup is designed for capital efficiency - reaching the right people without waste. "
                "The structure scales with you as budget grows, keeping CAC tight."
        )
        return f"{base_reply}\n\n{founder_frame}"

    return base_reply


def _finalize_reply(base_reply: str, session, state: str | None = None) -> str:
    """
    Add a non-repetitive, conversational closing move only if needed.
    - If the reply already ends with a question mark, do not append a move.
    - If the reply already ends with a known closing phrase, do not append another.
    - Otherwise, pick a state-appropriate closer and cycle to avoid repetition.
    """
    if not base_reply:
        return base_reply
    text = base_reply.rstrip()
    # Don't add closer if reply ends with a question
    if text.endswith("?"):
        return text
    lower = text.lower()
    # Common closers to check for duplication
    existing_closers = [
        "say the word",
        "ready when you are",
        "what would you like",
        "shall we",
        "just say go",
        "let me know",
        "your call",
        "confirm to proceed",
        "want me to",
    ]
    if any(c in lower[-80:] for c in existing_closers):
        return text

    # State-aware closers
    if state == ACTIVATION_STATE:
        closers = [
            "Confirm and I'll package it.",
            "Ready to lock this in.",
            "Your call on next steps.",
        ]
    elif state == OPTIMIZATION_STATE:
        closers = [
            "Let me know if you want another lever.",
            "We can adjust further if needed.",
        ]
    elif state == PROGRAM_GENERATION_STATE or state == REASONING_BRIDGE_STATE:
        closers = [
            "We can refine or move to activation — your call.",
            "Want to map activation next?",
            "Ready to take this into activation when you are.",
        ]
    elif state == EXIT_STATE:
        # No closer needed for exit
        return text
    else:
        # Generic closers for early states
        closers = [
            "Ready when you are.",
            "What's the brief?",
            "Drop the details and I'll build it.",
        ]

    idx = getattr(session, "last_closing_idx", 0) or 0
    choice = closers[idx % len(closers)]
    try:
        session.last_closing_idx = (idx + 1) % len(closers)
    except Exception:
        pass
    return f"{text}\n\n{choice}"

def _llm_next_state(
    previous_state: str,
    last_user: str,
    brand_name: str | None,
    brief: str | None,
    model_client=None,
) -> str | None:
    """
    Ask the model to decide the next behavioral state.
    Returns a state id string or None if parsing fails.
    """
    client = model_client or get_openai_client()
    system_content = (
        "You are MIRA, the RJM strategist, responsible for deciding the next interaction state.\n"
        "Valid states are:\n"
        "- STATE_GREETING\n- STATE_INPUT\n- STATE_CLARIFICATION\n- STATE_PROGRAM_GENERATION\n"
        "- STATE_REASONING_BRIDGE\n- STATE_ACTIVATION\n- STATE_OPTIMIZATION\n- STATE_EXIT\n\n"
        "Rules:\n"
        "- If brand and brief are missing, move toward CLARIFICATION.\n"
        "- If both brand and brief are present and the user is asking to build or proceed, move to PROGRAM_GENERATION.\n"
        "- After program summary, move to STATE_REASONING_BRIDGE.\n"
        "- If the user asks for activation mapping, move to STATE_REASONING_BRIDGE or STATE_ACTIVATION depending on flow.\n"
        "- After activation summary, stay in STATE_ACTIVATION unless the user accepts (then STATE_EXIT) or asks for changes (STATE_OPTIMIZATION).\n"
        "- If the user asks for scale/quality/delivery/frequency/geo adjustments, choose STATE_OPTIMIZATION.\n"
        "- Otherwise, choose the cleanest forward state.\n\n"
        "Return STRICT JSON only: {\"next_state\":\"<STATE_ID>\"} with one of the valid state ids above. No commentary."
    )
    user_content = (
        f"Previous state: {previous_state}\n"
        f"Brand present: {bool(brand_name)}\n"
        f"Brief present: {bool(brief)}\n"
        f"Last user message: {last_user!r}\n"
    )
    try:
        completion = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": get_canonical_system_prompt()},
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
        )
        content = completion.choices[0].message.content or ""
        import json as _json

        parsed = _json.loads(content)
        nxt = parsed.get("next_state")
        if isinstance(nxt, str) and nxt.startswith("STATE_"):
            return nxt
    except Exception:
        return None
    return None


def _classify_input_label(user_text: str) -> str:
    """
    Very lightweight input classification, to be refined over time.

    For v1:
    - If user explicitly mentions "activate", "activation", "deal id" → request_activation
    - Otherwise → complete
    """
    text = (user_text or "").lower()
    if any(word in text for word in ("activate", "activation", "deal id", "deal-id", "dealid")):
        return "request_activation"
    return "complete"


def _handle_greeting(_req: MiraChatRequest, _session) -> Tuple[str, str]:
    """
    Greeting state:
    - Let the model express the canonical greeting in MIRA's voice.
    """
    client = get_openai_client()

    # Use the canonical greeting text from the spec as a target,
    # but let the model render it (keeps Experience Layer in-model).
    canonical = get_initial_greeting()

    system_content = (
        "You are MIRA, the RJM strategist.\n"
        "Tone: calm, clean, confident. Short, intentional sentences. No emojis, no AI tropes, no apologies.\n"
        "Behavior: follow Anchor → Frame → Offer → Move.\n"
        "In this turn you are greeting a new user.\n"
        "Your greeting should:\n"
        "- Introduce yourself as MIRA.\n"
        "- Ask what campaign they are working on and what they need to achieve.\n"
        "- Invite them to drop in a brief, a few notes, or just the category.\n"
        "- Mention that you will turn it into an activation-ready audience plan built from RJM Personas.\n"
        "- Optionally mention you can also support programmatic activation if they share a DSP.\n"
        "Keep it under ~5 short lines.\n"
    )

    user_content = (
        "The canonical greeting copy from the spec is:\n"
        f"\"{canonical}\"\n\n"
        "Write one greeting in your own words that satisfies the bullets above. Plain text only."
    )

    completion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": get_canonical_system_prompt()},
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
    )
    reply = completion.choices[0].message.content or ""
    # Don't add a closer for greeting - the model's greeting should end with a question
    return reply, INPUT_STATE


def _handle_input(req: MiraChatRequest, session, session_id: str = None) -> Tuple[str, str, Optional[dict]]:
    user_text = _get_last_user_message(req.messages)

    # If we already have brand + brief, we can move straight into program generation.
    if req.brand_name and req.brief:
        return _handle_program_generation(req, session, session_id)

    # Otherwise, classify the input and route via the behavioral spec.
    label = _classify_input_label(user_text)
    next_state = classify_input_routing(label)

    if next_state == PROGRAM_GENERATION_STATE and req.brand_name and req.brief:
        return _handle_program_generation(req, session, session_id)

    # If we are missing brand / brief, go to clarification and let the model phrase the ask.
    client = get_openai_client()

    # Build conversation context
    conversation_context = _build_conversation_context(session_id) if session_id else ""

    system_content = (
        "You are MIRA, the RJM strategist, in the Input state.\n"
        "You do not yet have a brand name or a clear campaign brief.\n"
        "Ask ONE clean question that gets what you need to move forward.\n"
        "Tone: calm, clean, confident. No emojis, no AI tropes, no apologies.\n"
        "Behavior: Anchor → Frame → Offer → Move in a very compact way.\n"
        "- Anchor: acknowledge you see what they sent.\n"
        "- Frame: say what actually matters right now (brand + brief).\n"
        "- Offer: say what you'll do once you have it.\n"
        "- Move: ask the single question.\n"
        "If the user asks a general/definitional question (e.g., 'What are RJM Personas?'),\n"
        "first give a concise 1-3 sentence explanation, then ask your single required question to proceed.\n"
        "Keep it to 2–4 short sentences.\n\n"
        "IMPORTANT: Consider the conversation history to maintain context and avoid repeating yourself."
    )
    user_content = (
        f"{conversation_context}"
        f"The user just said:\n\"{user_text}\"\n\n"
        "Respond with one short message that follows these rules."
    )
    completion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": get_canonical_system_prompt()},
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
    )
    reply = completion.choices[0].message.content or ""
    # Model should end with a question; no extra closer needed
    return reply, CLARIFICATION_STATE, None


def _handle_clarification(req: MiraChatRequest, session, session_id: str = None) -> Tuple[str, str, Optional[dict]]:
    """
    Clarification logic is intentionally minimal:
    - If brand + brief now provided → move to program generation.
    - Otherwise, repeat a single clarifying question (one per turn).
    """
    if req.brand_name and req.brief:
        return _handle_program_generation(req, session, session_id)

    client = get_openai_client()
    last_user = _get_last_user_message(req.messages)

    # Build conversation context
    program_summary = get_program_summary(session_id) if session_id else None
    conversation_context = _build_conversation_context(session_id, program_summary) if session_id else ""

    system_content = (
        "You are MIRA, the RJM strategist, in the Clarification state.\n"
        "You still do not have enough detail to build a Persona Program.\n"
        "Ask ONE clean clarifying question to unblock the work.\n"
        "Tone: calm, clean, confident. No emojis, no AI tropes, no apologies.\n"
        "Behavior: very light Anchor → Frame → Move (no heavy Offer here).\n"
        "- Anchor: a brief \"Got it\"-style acknowledgement.\n"
        "- Frame: say you need either the brand, the brief, or both.\n"
        "- Move: ask the single question.\n"
        "If the user asks a general/definitional question (e.g., 'What are RJM Personas?'),\n"
        "first give a concise 1-3 sentence explanation, then finish with your single required question.\n"
        "Keep it to 1-3 short sentences.\n\n"
        "IMPORTANT: Consider the conversation history to maintain context and respond appropriately to what the user is asking."
    )
    user_content = (
        f"{conversation_context}"
        f"Latest user message:\n\"{last_user}\"\n\n"
        "Respond with one short message that follows these rules."
    )
    completion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": get_canonical_system_prompt()},
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
    )
    reply = completion.choices[0].message.content or ""
    # Model should end with a question; no extra closer needed
    return reply, CLARIFICATION_STATE, None


def _handle_program_generation(req: MiraChatRequest, session, session_id: str = None) -> Tuple[str, str, Optional[dict]]:
    """
    Call existing Packaging / RAG pipeline to generate the Persona Program,
    then present it in a MIRA-consistent way with a clear guiding move.
    
    Returns:
        Tuple of (reply, next_state, generation_data)
        generation_data is None if no program was generated, otherwise contains the program data for saving.
    """
    if not req.brand_name or not req.brief:
        # Behavioral correction: vague brief / missing inputs.
        correction = apply_correction_pattern("vague_brief") or (
            "I can work with more — give me the brand name and a short campaign brief."
        )
        return correction, CLARIFICATION_STATE, None

    app_logger.info(
        f"MIRA chat: generating persona program for brand={req.brand_name!r}"
    )

    program_json = generate_program_with_rag(
        GenerateProgramRequest(brand_name=req.brand_name, brief=req.brief)
    )

    header = program_json.header
    category = program_json.advertising_category or "this category"
    ki_preview = ", ".join(program_json.key_identifiers[:2]) if program_json.key_identifiers else ""

    # Build a summary of the generated program to store in session
    persona_names = [p.name for p in program_json.personas[:4]] if program_json.personas else []
    program_summary = (
        f"Brand: {req.brand_name}\n"
        f"Category: {category}\n"
        f"Header: {header}\n"
        f"Key Identifiers: {ki_preview}\n"
        f"Personas: {', '.join(persona_names)}"
    )

    # Store the program summary in session for later context
    if session_id:
        set_program_summary(session_id, program_summary)
    
    # Build generation data for saving
    # We need to build the full program text similar to the generate endpoint
    from app.services.rjm_ingredient_canon import (
        ALL_GENERATIONAL_NAMES,
        get_category_personas,
        get_dual_anchors,
        infer_category as infer_ad_category,
    )
    
    detected_category = category
    lines: list[str] = []
    lines.append(req.brand_name)
    lines.append("Persona Program")
    lines.append("⸻")
    
    clean_ki = [ki.rstrip(".").strip() for ki in (program_json.key_identifiers or [])[:2]]
    ki_preview_text = ", ".join(clean_ki) if clean_ki else ""
    base_context = ki_preview_text.lower() if ki_preview_text else "beauty, ritual, culture, and everyday expression"
    sentence1 = f"Curated for those who turn {base_context} into meaning, memory, and momentum."
    sentence2 = f"This {req.brand_name} program organizes those patterns into a clear, strategist-led framework for how the brand shows up in culture."
    write_up = f"{sentence1} {sentence2}"
    lines.append(write_up)
    lines.append("")
    
    lines.append("🔑 Key Identifiers")
    key_ids = list(program_json.key_identifiers or [])[:5]
    for identifier in key_ids:
        lines.append(f"• {identifier}")
    lines.append("")
    
    lines.append("✨ Persona Highlights")
    personas_with_highlight = [p for p in program_json.personas if getattr(p, "highlight", None)][:4]
    for p in personas_with_highlight:
        lines.append(f"{p.name} → {p.highlight}")
    lines.append("")
    
    lines.append("📊 Persona Insights")
    for insight in (program_json.persona_insights or []):
        lines.append(f"• {insight}")
    lines.append("")
    
    lines.append("👥 Demos")
    lines.append(f"• Core : {program_json.demos.get('core') or 'Adults 25–54'}")
    lines.append(f"• Secondary : {program_json.demos.get('secondary') or 'Adults 18+'}")
    lines.append("")
    
    lines.append("📍 Persona Portfolio")
    portfolio_names = [p.name for p in program_json.personas[:15]]
    lines.append(" · ".join(portfolio_names))
    lines.append("")
    lines.append("⸻")
    
    program_text = "\n".join(lines)
    
    generation_data = {
        "brand_name": req.brand_name,
        "brief": req.brief,
        "program_text": program_text,
        "program_json": program_json.model_dump_json(),
        "advertising_category": detected_category,
    }

    # Let GPT write the strategist-facing program summary + bridge.
    client = get_openai_client()
    last_user = _get_last_user_message(req.messages)
    mode = _detect_mode(last_user)

    # Build conversation context
    conversation_context = _build_conversation_context(session_id) if session_id else ""

    mode_hint = (
        "Trader"
        if mode == "trader"
        else "SMB" if mode == "smb" else "General strategist (no special mode)."
    )

    system_content = (
        "You are MIRA, the RJM strategist.\n"
        "You have just finished building a full RJM Persona Program.\n"
        "Tone: calm, clean, confident. Short, intentional sentences. No emojis, no AI tropes, no apologies.\n"
        "Behavior: follow Anchor → Frame → Offer → Move.\n"
        "- Anchor: acknowledge that the program is built.\n"
        "- Frame: say, in one line, what this program is anchored in.\n"
        "- Offer: describe what the program does for the brand in this category.\n"
        "- Move: give the user two options: refine personas/brief, or map activation next.\n"
        "Do not show JSON or schema. One compact paragraph is enough.\n\n"
        "IMPORTANT: Consider the conversation history to maintain context."
    )
    user_content = (
        f"{conversation_context}"
        f"User mode hint: {mode_hint}\n"
        f"Brand: {req.brand_name}\n"
        f"Category: {category}\n"
        f"Program header: {header}\n"
        f"Anchored in: {ki_preview or 'the core cultural and behavioral patterns you see in the brief.'}\n\n"
        "Write one reply that follows the rules above."
    )
    completion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": get_canonical_system_prompt()},
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
    )
    base_reply = completion.choices[0].message.content or ""

    reply = _apply_mode_styling(base_reply, mode)
    reply = _finalize_reply(reply, session, PROGRAM_GENERATION_STATE)
    return reply, REASONING_BRIDGE_STATE, generation_data


def _handle_reasoning_bridge(req: MiraChatRequest, session, session_id: str = None) -> Tuple[str, str]:
    """
    Reasoning Bridge → Activation:
    - Assume a clean awareness plan with balanced mix.
    - Build an Activation Summary Block via the activation JSON helpers.
    """
    if not req.brand_name or not req.brief:
        correction = apply_correction_pattern("vague_brief") or (
            "I can work with more — give me the brand name and a short campaign brief."
        )
        return correction, CLARIFICATION_STATE

    last_user = _get_last_user_message(req.messages)

    # Build a minimal activation plan from brand/brief and user context.
    plan = build_activation_plan(
        brand_name=req.brand_name,
        brief=req.brief,
        category=None,
        user_text=last_user,
    )

    # Let GPT write the strategist-facing activation copy (Experience Layer),
    # using the activation plan as structured input.
    client = get_openai_client()

    # Build conversation context
    program_summary = get_program_summary(session_id) if session_id else None
    conversation_context = _build_conversation_context(session_id, program_summary) if session_id else ""

    system_content = (
        "You are MIRA, the activation strategist for RJM.\n"
        "Tone: calm, clean, confident. Short, intentional sentences. No apologies, no emojis, no AI tropes.\n"
        "Behavior: follow Anchor → Frame → Offer → Move.\n"
        "- Anchor: briefly acknowledge where we are.\n"
        "- Frame: one short line on what actually matters.\n"
        "- Offer: PRESENT THE ACTIVATION PLAN ONLY, using the provided fields. Do NOT restate or rebuild the Persona Program; do not ask the user what to do next before giving the activation.\n"
        "- Move: close with one clear next step the user can take (e.g., confirm to proceed with packaging/deal IDs or adjust a lever).\n"
        "Guardrails: stay inside strategy only. Do not describe trafficking steps, bidding mechanics, or DSP UI flows. "
        "Do not invent budgets or KPIs. Do not reference internal system names.\n"
        "If the user said anything like 'map activation' or 'activate', proceed directly with the activation summary; do not re-offer to map activation.\n\n"
        "IMPORTANT: Consider the conversation history and respond appropriately to what the user is asking."
    )

    user_content = (
        f"{conversation_context}"
        f"The Persona Program for brand '{req.brand_name}' is approved. "
        f"The user just said: '{last_user}'.\n\n"
        "Here is the activation plan you must express:\n"
        f"- Platform Path: {plan.platform_path}\n"
        f"- Budget Window: {plan.budget_window}\n"
        f"- Pacing Mode: {plan.pacing_mode}\n"
        f"- Flighting Cadence: {plan.flighting_cadence}\n"
        f"- Persona Deployment: {plan.persona_deployment}\n"
        f"- Channel Deployment: {plan.channel_deployment}\n"
        f"- Packaging: {plan.deal_id_or_packaging}\n"
        f"- Why it works: {plan.activation_rationale}\n\n"
        "Write one strategist-facing reply that:\n"
        "- Starts with Anchor, then Frame, then Offer, then Move.\n"
        "- Clearly covers the platform path, budget window, pacing, flighting, persona deployment, channel deployment, and why it works.\n"
        "- Is concise and calm.\n"
        "- Does not show JSON or code. Plain text only.\n"
        "- If the user asked a question, answer it first before presenting the plan."
    )

    try:
        completion = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            messages=[
                {"role": "system", "content": get_canonical_system_prompt()},
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
        )
        base_reply = completion.choices[0].message.content or ""
    except Exception as exc:  # pragma: no cover - defensive fallback
        app_logger.error(f"Activation LLM call failed: {exc}")
        # Fallback: simple text if model fails
        base_reply = (
            "Here's how this plan should launch: "
            f"{plan.platform_path} with a single budget window, standard pacing and linear flighting, "
            "primary personas in CTV/OLV and support personas in Audio/Display. "
            "This protects identity while giving you clean awareness and enough room to move."
        )

    mode = _detect_mode(last_user)
    reply = _apply_mode_styling(base_reply, mode)
    reply = _finalize_reply(reply, session, ACTIVATION_STATE)
    return reply, ACTIVATION_STATE


def _handle_activation_state(req: MiraChatRequest, session, session_id: str = None) -> Tuple[str, str]:
    """
    Activation state:
    - If user signals acceptance → EXIT.
    - If user asks for more performance/scale tweaks → go to OPTIMIZATION.
    """
    last_user = _get_last_user_message(req.messages)
    text = last_user.lower()

    # Build conversation context
    program_summary = get_program_summary(session_id) if session_id else None
    conversation_context = _build_conversation_context(session_id, program_summary) if session_id else ""

    if any(
        phrase in text
        for phrase in (
            "looks good",
            "good to go",
            "run it",
            "ship it",
            "that works",
            "okay",
            "ok",
            "sounds good",
        )
    ):
        client = get_openai_client()
        system_content = (
            "You are MIRA, the RJM strategist, closing an activation conversation.\n"
            "Tone: calm, clean, confident. No emojis, no AI tropes, no apologies.\n"
            "You should:\n"
            "- Briefly acknowledge that the setup works.\n"
            "- Close with a sense of continuity (you'll be there for the next move).\n"
            "Do NOT ask \"Is there anything else?\" or use customer-service language.\n"
            "One short line is enough.\n\n"
            "IMPORTANT: Consider the conversation history."
        )
        user_content = (
            f"{conversation_context}"
            f"The user just said: \"{last_user}\" and is clearly accepting the plan."
        )
        completion = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            messages=[
                {"role": "system", "content": get_canonical_system_prompt()},
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
        )
        reply = completion.choices[0].message.content or ""
        return _finalize_reply(reply, session, EXIT_STATE), EXIT_STATE

    # Anything else in Activation is treated as a request for a clean adjustment.
    return _handle_optimization_state(req, session, session_id)


def _handle_optimization_state(req: MiraChatRequest, session, session_id: str = None) -> Tuple[str, str]:
    """
    Handle optimization requests with context-aware, LLM-driven responses.
    Uses World Model context for mode-appropriate responses.
    Responds specifically to what the user is asking about (scale, quality, reach, etc.)
    """
    last_user = _get_last_user_message(req.messages)
    client = get_openai_client()
    mode = _detect_mode(last_user)
    mode_hint = (
        "Trader"
        if mode == "trader"
        else "SMB" if mode == "smb" else "General strategist (no special mode)."
    )

    # Build conversation context
    program_summary = get_program_summary(session_id) if session_id else None
    conversation_context = _build_conversation_context(session_id, program_summary) if session_id else ""
    
    # Get World Model context for mode-aware prompting
    world_model_context = _build_mode_aware_system_context(mode, session)

    system_content = (
        "You are MIRA, the RJM strategist, helping optimize a campaign.\n"
        "Tone: calm, clean, confident. Short, intentional sentences. No emojis, no AI tropes, no apologies.\n\n"
        f"{world_model_context}\n\n"
        "CRITICAL: Read the user's actual request and respond SPECIFICALLY to what they're asking.\n\n"
        "Common optimization requests and how to respond:\n"
        "- 'More scale/reach': Explain how to widen persona emphasis and add OLV/Display weight.\n"
        "- 'Better quality/right people': Explain how to tighten persona targeting toward higher-intent segments.\n"
        "- 'Messaging strategies': Give SPECIFIC creative angles, tones, and messaging themes for their brand.\n"
        "- 'Channels and pacing': Explain the specific channel mix (CTV %, OLV %, Audio %, Display %) and pacing cadence.\n"
        "- General questions: Answer them directly and helpfully.\n\n"
        "Behavior: Anchor → Frame → Offer → Move.\n"
        "- Anchor: Acknowledge what they're asking about.\n"
        "- Frame: State what aspect you're addressing.\n"
        "- Offer: Give specific, actionable guidance tailored to their brand and situation.\n"
        "- Move: Close with a clear next step or offer to help with another aspect.\n\n"
        "AVOID: Generic responses. Do not give the same advice regardless of what they ask.\n"
        "If they ask about messaging, give messaging advice. If they ask about reach, give reach advice."
    )
    
    user_content = (
        f"{conversation_context}\n\n"
        f"User mode: {mode_hint}\n"
        f"Brand: {req.brand_name or 'Unknown'}\n"
        f"Brief: {req.brief or 'Not specified'}\n\n"
        f"User's request: \"{last_user}\"\n\n"
        "Respond specifically to what they're asking. Be concrete and helpful."
    )

    completion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": get_canonical_system_prompt()},
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
    )
    base_reply = completion.choices[0].message.content or ""

    reply = _apply_mode_styling(base_reply, mode)
    return _finalize_reply(reply, session, OPTIMIZATION_STATE), OPTIMIZATION_STATE


def _handle_question(req: MiraChatRequest, session, session_id: str, current_state: str) -> Tuple[str, str]:
    """
    Handle user questions contextually - answer the question and maintain flow.
    """
    last_user = _get_last_user_message(req.messages)
    client = get_openai_client()

    # Build conversation context
    program_summary = get_program_summary(session_id) if session_id else None
    conversation_context = _build_conversation_context(session_id, program_summary) if session_id else ""

    system_content = (
        "You are MIRA, the RJM strategist.\n"
        "The user has asked a question. Answer it directly and concisely.\n"
        "Tone: calm, clean, confident. Short, intentional sentences. No emojis, no AI tropes, no apologies.\n\n"
        "Key definitions you should know:\n"
        "- RJM Personas: Identity- and culture-based audience archetypes built from behavioral signals, "
        "not just demographics. They represent how people actually signal meaning and make decisions.\n"
        "- Activation: The process of deploying personas through media channels (CTV, OLV, Audio, Display) "
        "with specific pacing, flighting, and targeting strategies.\n"
        "- Funnel stages: Upper (awareness), Mid (consideration), Lower (conversion).\n\n"
        "After answering, briefly offer to continue with the next logical step based on where we are in the conversation.\n"
        "Keep your answer to 2-4 sentences."
    )

    user_content = (
        f"{conversation_context}"
        f"Current conversation state: {current_state}\n"
        f"User's question: \"{last_user}\"\n\n"
        "Answer the question directly, then offer to continue."
    )

    completion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": get_canonical_system_prompt()},
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
    )
    reply = completion.choices[0].message.content or ""

    # Stay in the same state after answering a question
    return reply, current_state


def _handle_acceptance(req: MiraChatRequest, session, session_id: str) -> Tuple[str, str]:
    """
    Handle user acceptance/approval - close the conversation gracefully.
    """
    last_user = _get_last_user_message(req.messages)
    client = get_openai_client()

    # Build conversation context
    program_summary = get_program_summary(session_id) if session_id else None
    conversation_context = _build_conversation_context(session_id, program_summary) if session_id else ""

    system_content = (
        "You are MIRA, the RJM strategist, closing a conversation.\n"
        "The user has accepted/approved the plan.\n"
        "Tone: calm, clean, confident. No emojis, no AI tropes, no apologies.\n"
        "You should:\n"
        "- Briefly acknowledge that everything is set.\n"
        "- Mention the next operational step (packaging will be ready, or they can reach back when ready to launch).\n"
        "- Close with a sense of continuity (you'll be there for the next move).\n"
        "Do NOT ask 'Is there anything else?' or use customer-service language.\n"
        "One short paragraph (2-3 sentences) is enough."
    )

    user_content = (
        f"{conversation_context}"
        f"The user just said: \"{last_user}\" - they are clearly accepting/approving the plan."
    )

    completion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": get_canonical_system_prompt()},
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
    )
    reply = completion.choices[0].message.content or ""
    return reply, EXIT_STATE


def _handle_gratitude_exit(req: MiraChatRequest, session, session_id: str) -> Tuple[str, str]:
    """
    Handle user expressing gratitude and ending the conversation.
    """
    last_user = _get_last_user_message(req.messages)
    client = get_openai_client()

    # Build conversation context
    program_summary = get_program_summary(session_id) if session_id else None
    conversation_context = _build_conversation_context(session_id, program_summary) if session_id else ""

    system_content = (
        "You are MIRA, the RJM strategist.\n"
        "The user is expressing gratitude and ending the conversation.\n"
        "Tone: calm, clean, confident. No emojis, no AI tropes, no apologies.\n"
        "You should:\n"
        "- Warmly acknowledge their thanks in a brief, genuine way.\n"
        "- Confirm they're all set for now.\n"
        "- Leave the door open for future work without being pushy.\n"
        "Do NOT ask 'Is there anything else?' or use customer-service language.\n"
        "Keep it very short - 1-2 sentences max."
    )

    user_content = (
        f"{conversation_context}"
        f"The user just said: \"{last_user}\" - they are thanking you and ending the conversation."
    )

    completion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": get_canonical_system_prompt()},
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
    )
    reply = completion.choices[0].message.content or ""
    return reply, EXIT_STATE


def _handle_continuation(
    req: MiraChatRequest, session, session_id: str, current_state: str, last_mira_message: str | None
) -> Tuple[str, str]:
    """
    Handle user agreeing to continue on the current topic (e.g., "yes", "sure" after MIRA offers something).
    Uses MIRA's last message to understand what to continue with.
    """
    last_user = _get_last_user_message(req.messages)
    client = get_openai_client()

    # Build conversation context
    program_summary = get_program_summary(session_id) if session_id else None
    conversation_context = _build_conversation_context(session_id, program_summary) if session_id else ""

    # Determine what MIRA offered to do
    system_content = (
        "You are MIRA, the RJM strategist.\n"
        "The user just agreed to continue on the topic you offered.\n"
        "Tone: calm, clean, confident. Short, intentional sentences. No emojis, no AI tropes, no apologies.\n"
        "Behavior: follow Anchor → Frame → Offer → Move.\n\n"
        "CRITICAL: Look at your last message to see what you offered to do, then DO IT.\n"
        "- If you offered to discuss channels/pacing → Explain the specific channels (CTV, OLV, Audio, Display) and how pacing works for their campaign.\n"
        "- If you offered to discuss messaging strategies → Give concrete messaging angles and creative directions for their brand.\n"
        "- If you offered to map activation → Present the full activation plan with channels, timing, and deployment.\n"
        "- If you offered to refine → Ask what specifically they want to change.\n\n"
        "Do NOT give generic optimization advice unless they specifically asked for optimization.\n"
        "Be specific and actionable. Actually deliver what you promised."
    )

    user_content = (
        f"{conversation_context}\n\n"
        f"YOUR LAST MESSAGE WAS:\n\"{last_mira_message}\"\n\n"
        f"The user responded: \"{last_user}\" (agreeing to what you offered)\n\n"
        "Now deliver what you offered. Be specific and helpful."
    )

    completion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": get_canonical_system_prompt()},
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
    )
    reply = completion.choices[0].message.content or ""

    # Determine next state based on current state and context
    # Generally stay in the same state or progress naturally
    if current_state == PROGRAM_GENERATION_STATE:
        next_state = REASONING_BRIDGE_STATE  # Move to activation
    elif current_state == REASONING_BRIDGE_STATE:
        next_state = ACTIVATION_STATE
    else:
        next_state = current_state  # Stay in current state

    return _finalize_reply(reply, session, next_state), next_state


def _log_state_transition(
    session_id: str,
    previous_state: str,
    next_state: str,
    brand_name: str | None,
    mode: str | None,
    turn_count: int,
) -> None:
    """Log state transition for monitoring and debugging."""
    app_logger.info(
        "MIRA state transition",
        extra={
            "session_id": session_id,
            "previous_state": previous_state,
            "next_state": next_state,
            "brand_name": brand_name,
            "mode": mode,
            "turn_count": turn_count,
            "event_type": "state_transition",
        },
    )


def handle_chat_turn(req: MiraChatRequest, user_id: Optional[str] = None) -> MiraChatResponse:
    """
    Entry point for the FastAPI router.

    This function interprets the current behavioral state and returns
    MIRA's reply plus the next state id.
    
    Args:
        req: The chat request with messages and state
        user_id: Optional user ID for saving persona generations
    
    Returns:
        MiraChatResponse with reply, state, and optional generation_data
    """
    import time
    start_time = time.time()
    
    # Track generation data for saving
    generation_data = None

    # Resolve or create session
    session_id, session = get_session(req.session_id)

    # If client didn't pass brand/brief, use session memory
    if not req.brand_name and session.brand_name:
        req.brand_name = session.brand_name
    if not req.brief and session.brief:
        req.brief = session.brief

    previous_state = req.state or GREETING_STATE

    # Store the user's message in conversation history
    last_user_msg_content = _get_last_user_message(req.messages)
    if last_user_msg_content:
        add_message_to_history(session_id, "user", last_user_msg_content)

    # Get MIRA's last message for context-aware intent detection
    conversation_history = get_conversation_history(session_id)
    last_mira_message = None
    for msg in reversed(conversation_history):
        if msg.get("role") == "assistant":
            last_mira_message = msg.get("content", "")
            break

    # Build conversation context for intent detection
    program_summary = get_program_summary(session_id) if session_id else None
    conversation_context = _build_conversation_context(session_id, program_summary) if session_id else ""

    # INTENT-BASED ROUTING: Use LLM to detect user intent with full context
    user_intent = _detect_user_intent_llm(
        user_text=last_user_msg_content,
        conversation_context=conversation_context,
        current_state=previous_state,
        last_mira_message=last_mira_message,
    )
    app_logger.info(f"LLM detected intent: {user_intent} for message: {last_user_msg_content[:50]}...")

    # Check if we have a program generated (determines if acceptance makes sense)
    has_program = session.program_generated or get_program_summary(session_id) is not None

    # Intent-based routing takes priority over state-based routing
    if user_intent == "gratitude_exit":
        # User is thanking and ending - close gracefully
        reply, next_state = _handle_gratitude_exit(req, session, session_id)

    elif user_intent == "question":
        # Handle questions directly - answer and stay in flow
        reply, next_state = _handle_question(req, session, session_id, previous_state)

    elif user_intent == "acceptance" and has_program:
        # User is accepting - close the conversation gracefully
        reply, next_state = _handle_acceptance(req, session, session_id)

    elif user_intent == "continuation":
        # User is agreeing to continue on the current topic - respond contextually
        reply, next_state = _handle_continuation(req, session, session_id, previous_state, last_mira_message)

    elif user_intent == "activation_request" and req.brand_name and req.brief:
        # User wants activation mapping
        reply, next_state = _handle_reasoning_bridge(req, session, session_id)

    elif user_intent == "optimization" and has_program:
        # User wants to optimize/adjust
        reply, next_state = _handle_optimization_state(req, session, session_id)

    # Fall back to state-based routing for general inputs
    elif previous_state == GREETING_STATE:
        reply, next_state = _handle_greeting(req, session)

    elif previous_state == INPUT_STATE:
        reply, next_state, generation_data = _handle_input(req, session, session_id)

    elif previous_state == CLARIFICATION_STATE:
        # If we now have brand + brief, move to program generation
        if req.brand_name and req.brief:
            reply, next_state, generation_data = _handle_program_generation(req, session, session_id)
        else:
            reply, next_state, generation_data = _handle_clarification(req, session, session_id)

    elif previous_state == PROGRAM_GENERATION_STATE:
        # Program was shown, user is responding - check what they want
        if req.brand_name and req.brief:
            # Default: show activation mapping as next step
            reply, next_state = _handle_reasoning_bridge(req, session, session_id)
        else:
            reply, next_state = _handle_clarification(req, session, session_id)

    elif previous_state == REASONING_BRIDGE_STATE:
        # Activation was shown, continue in activation flow
        reply, next_state = _handle_activation_state(req, session, session_id)

    elif previous_state == ACTIVATION_STATE:
        # Safety check: catch gratitude patterns that slipped through intent detection
        text_lower = last_user_msg_content.lower() if last_user_msg_content else ""
        if any(p in text_lower for p in ("thank", "good for now", "i'm done", "im done", "that's all", "thats all")):
            reply, next_state = _handle_gratitude_exit(req, session, session_id)
        else:
            reply, next_state = _handle_activation_state(req, session, session_id)

    elif previous_state == OPTIMIZATION_STATE:
        # Safety check: catch gratitude patterns that slipped through intent detection
        text_lower = last_user_msg_content.lower() if last_user_msg_content else ""
        if any(p in text_lower for p in ("thank", "good for now", "i'm done", "im done", "that's all", "thats all")):
            reply, next_state = _handle_gratitude_exit(req, session, session_id)
        else:
            reply, next_state = _handle_optimization_state(req, session, session_id)

    elif previous_state == EXIT_STATE:
        # Already exited, but user sent another message - restart flow
        reply, next_state = _handle_greeting(req, session)

    else:
        # Fallback: treat unknown state as neutral and re-anchor.
        correction = apply_correction_pattern("vague_brief") or (
            "Here's where we were - let's pick it back up cleanly."
        )
        reply = correction
        next_state = INPUT_STATE

    # Store MIRA's reply in conversation history
    if reply:
        add_message_to_history(session_id, "assistant", reply)

    # DISABLED: LLM state chooser was causing random state jumps
    # The intent-based routing above provides more natural conversation flow
    # Only use LLM state chooser as a fallback for truly ambiguous cases
    # (Currently disabled to test pure intent-based flow)

    # After that, try to extract brand/brief using a small LLM extractor if still missing
    # This keeps "experience layer" in-model while we capture memory server-side.
    try:
        if not req.brand_name or not req.brief:
            extractor = get_openai_client()
            convo_text = "\n".join([f"{m.role.upper()}: {m.content}" for m in req.messages])
            extract_system = (
                "Extract the brand name and campaign brief from the conversation.\n"
                "Return STRICT JSON with fields: brand_name (string|null), brief (string|null).\n"
                "If unknown, use null. Do not add commentary."
            )
            extract_user = f"Conversation:\n{convo_text}"
            extract_resp = extractor.chat.completions.create(
                model=settings.OPENAI_MODEL,
                temperature=0,
                messages=[
                    {"role": "system", "content": extract_system},
                    {"role": "user", "content": extract_user},
                ],
            )
            content = extract_resp.choices[0].message.content or "{}"
            import json as _json

            try:
                parsed = _json.loads(content)
                b = parsed.get("brand_name")
                br = parsed.get("brief")
                if not req.brand_name and b:
                    update_session(session_id, brand_name=b)
                if not req.brief and br:
                    update_session(session_id, brief=br)
            except Exception:
                pass
        else:
            update_session(session_id, brand_name=req.brand_name, brief=req.brief)
    except Exception:
        # Never crash the chat on extractor errors
        pass

    # Log state transition for monitoring
    elapsed_ms = int((time.time() - start_time) * 1000)
    mode = _detect_mode(last_user_msg_content)
    _log_state_transition(
        session_id=session_id,
        previous_state=previous_state,
        next_state=next_state,
        brand_name=req.brand_name or session.brand_name,
        mode=mode,
        turn_count=session.turn_count,
    )
    app_logger.info(
        "MIRA chat turn completed",
        extra={
            "session_id": session_id,
            "elapsed_ms": elapsed_ms,
            "previous_state": previous_state,
            "next_state": next_state,
            "event_type": "chat_turn_complete",
        },
    )

    return MiraChatResponse(
        reply=reply,
        state=next_state,
        session_id=session_id,
        debug_state_was=previous_state,
        generation_data=generation_data,
    )



