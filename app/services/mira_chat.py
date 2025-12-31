"""
MIRA Chat - LLM-Driven Conversational Engine.

This module implements a natural, conversational AI experience where the LLM
drives the conversation with marketing/business intelligence as a background mission.

Key Design Principles:
- LLM decides the flow, not a rigid state machine
- Rich system prompt provides behavioral guidance without forcing transitions
- Persona generation and activation are TOOLS the LLM can invoke when appropriate
- Natural conversation first, deliverables emerge organically

Architecture:
- OpenAI function/tool calling for deliverables (personas, activation plans)
- Session memory for conversation context
- Behavioral specs as guidance, not hard control
"""

from __future__ import annotations

import json
from typing import List, Tuple, Optional, Any, Dict
from uuid import uuid4

from app.api.rjm.schemas import (
    ChatMessage,
    GenerateProgramRequest,
    MiraChatRequest,
    MiraChatResponse,
)
from app.config.logger import app_logger
from app.config.settings import settings
from app.services.rjm_rag import generate_program_with_rag
from app.services.rjm_vector_store import get_openai_client
from app.services.mira_activation import build_activation_plan, format_activation_summary_block
from app.services.mira_session import (
    get_session,
    update_session,
    add_message_to_history,
    get_conversation_history,
    set_program_summary,
    get_program_summary,
)


# ════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS FOR OPENAI FUNCTION CALLING
# ════════════════════════════════════════════════════════════════════════════

MIRA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_category_insights",
            "description": (
                "Get deep category intelligence and behavioral insights from the World Model. "
                "Use this when the user wants to understand: "
                "1) Their category's behavioral dynamics and tensions, "
                "2) How identity vs utility plays in their space, "
                "3) What channels work best for their category, "
                "4) Audience behavior patterns in their industry. "
                "This provides strategic intelligence WITHOUT generating formal deliverables."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "The advertising/industry category (e.g., QSR, Beauty, Auto, Retail)"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context about what insights the user needs"
                    }
                },
                "required": ["category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_persona_program",
            "description": (
                "Generate an RJM Persona Program for a brand. Use this when: "
                "1) The user has provided enough context about their brand/campaign, "
                "2) The conversation has naturally led to a point where a persona program would be valuable, "
                "3) The user explicitly asks for personas or a program. "
                "Do NOT force this - only call when it genuinely fits the conversation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "brand_name": {
                        "type": "string",
                        "description": "The brand name for the persona program"
                    },
                    "brief": {
                        "type": "string",
                        "description": "Campaign brief, objectives, or context for the program"
                    }
                },
                "required": ["brand_name", "brief"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_activation_plan",
            "description": (
                "Create a structured media activation plan using the Reasoning Engine decision trees. "
                "MUST USE THIS when user asks about: "
                "1) How to reach their audience / channels / media planning, "
                "2) How to activate or deploy personas, "
                "3) Media mix, CTV, OLV, Audio, Display allocation, "
                "4) Campaign execution, pacing, flighting, budget structure. "
                "This provides decision-tree-backed recommendations with specific percentages "
                "and rationale - NOT generic marketing advice. Use this instead of giving "
                "generic social media or email marketing suggestions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "brand_name": {
                        "type": "string",
                        "description": "The brand name"
                    },
                    "brief": {
                        "type": "string",
                        "description": "Campaign brief or objectives"
                    },
                    "category": {
                        "type": "string",
                        "description": "Advertising category (e.g., Beauty, Auto, QSR)"
                    },
                    "kpi": {
                        "type": "string",
                        "description": "Primary KPI if mentioned (awareness, consideration, conversion)"
                    },
                    "budget": {
                        "type": "number",
                        "description": "Budget amount if mentioned"
                    },
                    "timeline": {
                        "type": "string",
                        "description": "Campaign timeline if mentioned"
                    }
                },
                "required": ["brand_name", "brief"]
            }
        }
    }
]


# ════════════════════════════════════════════════════════════════════════════
# RICH SYSTEM PROMPT - THE SOUL OF MIRA
# ════════════════════════════════════════════════════════════════════════════

def _detect_user_mode(conversation_text: str) -> str:
    """
    Detect user mode from conversation signals.

    Modes from behavioral spec:
    - trader: DSP/media buying terminology (CPM, deal ID, TTD, DV360)
    - planner: Strategic/cultural language (tension, insight, segmentation)
    - creative: Narrative/storytelling focus (brand voice, concept, emotional)
    - smb: Small business signals (my shop, small budget, local business)
    - founder: Startup language (scale, growth, runway, CAC)
    """
    text = conversation_text.lower()

    # Trader mode: DSP terminology
    if any(w in text for w in ("cpm", "deal id", "ttd", "dv360", "dsp", "programmatic", "pmp")):
        return "trader"

    # SMB mode: small business signals
    if any(w in text for w in ("my restaurant", "my shop", "small business", "local", "budget", "not too much", "investment wise", "cost")):
        return "smb"

    # Founder mode: startup/growth language
    if any(w in text for w in ("scale", "startup", "founder", "growth", "cac", "runway", "series")):
        return "founder"

    # Planner mode: strategic language
    if any(w in text for w in ("tension", "insight", "segmentation", "positioning", "cultural")):
        return "planner"

    # Creative mode: narrative language
    if any(w in text for w in ("narrative", "storytelling", "brand voice", "concept", "emotional", "creative")):
        return "creative"

    return "general"


def _get_mode_instructions(mode: str) -> str:
    """Get mode-specific tone instructions from behavioral spec."""
    mode_instructions = {
        "trader": (
            "User is a TRADER (media buyer). Keep responses tight and operational. "
            "Use DSP terminology freely. No extra explanation layers. Trust their programmatic fluency."
        ),
        "smb": (
            "User is SMB (small business owner). Use plain language. Avoid marketing jargon. "
            "Be direct and actionable. Explain what things mean in simple terms. "
            "Focus on what they should actually DO. Be mindful of budget constraints."
        ),
        "founder": (
            "User is a FOUNDER. Emphasize efficiency, growth, and ROI. "
            "Focus on capital efficiency and CAC. Show how strategies scale with budget."
        ),
        "planner": (
            "User is a PLANNER (strategist). Add cultural and strategic framing. "
            "Emphasize tensions and insights. Connect personas to identity and meaning."
        ),
        "creative": (
            "User is a CREATIVE. Emphasize narrative and brand expression. "
            "Connect personas to storytelling opportunities. Highlight emotional centers."
        ),
    }
    return mode_instructions.get(mode, "")


def _infer_category_from_context(brand_name: str, brief: str) -> str:
    """Infer advertising category from brand and brief context."""
    from app.services.rjm_ingredient_canon import infer_category
    context = f"{brand_name} {brief}"
    return infer_category(context)


def _get_category_intelligence(category: str) -> str:
    """Get category-specific intelligence from World Model."""
    from app.services.mira_world_model import (
        get_category_profile,
        get_category_funnel_bias,
        get_identity_forward_categories,
        get_utility_forward_categories,
    )

    profile = get_category_profile(category)
    funnel_bias = get_category_funnel_bias(category)
    identity_forward = get_identity_forward_categories()
    utility_forward = get_utility_forward_categories()

    is_identity = category in identity_forward
    is_utility = category in utility_forward

    parts = [f"Category: {category}"]

    if profile:
        parts.append(f"Mix bias: {profile.get('mix_bias', 'balanced')}")
        parts.append(f"Funnel bias: {profile.get('funnel_bias', funnel_bias)}")
        if profile.get('behavioral_tension'):
            parts.append(f"Core tension: {profile.get('behavioral_tension')}")

    if is_identity:
        parts.append("Category type: Identity-forward (emotional, aspirational)")
    elif is_utility:
        parts.append("Category type: Utility-forward (functional, practical)")

    return "\n".join(parts)


def build_mira_system_prompt(session_context: dict = None) -> str:
    """
    Build the comprehensive MIRA system prompt that guides behavior without
    forcing a rigid state machine.

    This prompt embodies:
    - MIRA's identity and philosophy
    - Behavioral grammar (Anchor → Frame → Offer → Move)
    - World model awareness (category intelligence, funnel logic)
    - Marketing intelligence mission
    - Conversational flexibility
    - Mode-aware communication
    """
    from app.services.mira_world_model import (
        get_mira_posture,
        get_interpretation_principles,
        get_mix_template,
    )

    # Get MIRA's posture from World Model
    posture = get_mira_posture()

    # Build context section if we have session data
    context_section = ""
    category_intelligence = ""
    mode_instructions = ""

    if session_context:
        parts = []
        if session_context.get("brand_name"):
            parts.append(f"Current brand: {session_context['brand_name']}")
        if session_context.get("brief"):
            parts.append(f"Brief: {session_context['brief']}")

        # Infer category if we have brand/brief
        if session_context.get("brand_name") and session_context.get("brief"):
            category = _infer_category_from_context(
                session_context["brand_name"],
                session_context["brief"]
            )
            session_context["category"] = category
            category_intelligence = _get_category_intelligence(category)

        if session_context.get("category"):
            parts.append(f"Category: {session_context['category']}")
        if session_context.get("program_generated"):
            parts.append("Status: Persona program has been generated")
        if session_context.get("activation_shown"):
            parts.append("Status: Activation plan has been shown")

        # Mode detection from conversation
        if session_context.get("conversation_text"):
            mode = _detect_user_mode(session_context["conversation_text"])
            if mode != "general":
                mode_instructions = f"\n\nUSER MODE DETECTED: {mode.upper()}\n{_get_mode_instructions(mode)}"

        if parts:
            context_section = f"\n\nCURRENT CONTEXT:\n" + "\n".join(parts)

        # Add conversational phase guidance
        phase = session_context.get("conversational_phase", "EXPERIENCE")
        phase_guidance = {
            "EXPERIENCE": "Current phase: EXPERIENCE - Gather brand, brief, objectives. When you have enough, move to REASONING.",
            "REASONING": "Current phase: REASONING - You have brand/brief. Apply category insights. Then MOVE TO PACKAGING.",
            "PACKAGING": "Current phase: PACKAGING - Generate the persona program NOW. Don't ask permission.",
            "ACTIVATION": "Current phase: ACTIVATION - Program generated. Help with channels, media mix, deployment.",
            "COMPLETE": "Current phase: COMPLETE - Full journey done. Answer questions, refine, or start new project."
        }
        context_section += f"\n\n{phase_guidance.get(phase, '')}"

        if category_intelligence:
            context_section += f"\n\nCATEGORY INTELLIGENCE:\n{category_intelligence}"

    return f"""You are MIRA — RJM's strategist and business intelligence partner.

═══════════════════════════════════════════════════════════════════════════════
WHAT IS RJM? (If user asks)
═══════════════════════════════════════════════════════════════════════════════

RJM stands for Real Juice Media. RJM is an audience intelligence and media activation company
that specializes in identity-driven advertising. Key points:

- RJM has 200+ proprietary audience personas based on cultural identity signals
- RJM offers "Direct via RJM" activation - where RJM manages campaign execution with
  premium inventory access, quality assurance, and optimized pacing
- RJM personas are real, addressable audience segments (not just descriptive labels)
- RJM integrates with DSPs or can activate directly for brands/agencies

If user asks "What is RJM?" or "What does RJM activation mean?" - explain this clearly.
Don't just repeat "RJM-managed" without explaining what RJM actually is.

═══════════════════════════════════════════════════════════════════════════════
CORE IDENTITY
═══════════════════════════════════════════════════════════════════════════════

You are a strategic thinking partner who helps businesses understand their audiences
and develop marketing strategies rooted in cultural identity and behavioral insights.

Your expertise:
- Deep understanding of how people signal identity through behavior and consumption
- Cultural intelligence that goes beyond demographics
- Strategic media planning grounded in identity-first thinking
- The RJM Persona system - identity-based audience archetypes

Your mission: Provide brilliant business intelligence through natural conversation.
The persona programs and activation plans are TOOLS you can use - not the forced
destination of every conversation.

═══════════════════════════════════════════════════════════════════════════════
BEHAVIORAL PHILOSOPHY
═══════════════════════════════════════════════════════════════════════════════

TONE: Calm, clean, confident. Short, intentional sentences.
- No emojis
- No AI apologies ("I apologize", "I'm sorry")
- No customer-service language ("Is there anything else?", "How can I help?")
- No rambling or over-explaining
- Direct but warm

CONVERSATION GRAMMAR (when delivering substantial content):
1. Anchor — Acknowledge what the user said
2. Frame — State what actually matters
3. Offer — Present your insight, plan, or perspective
4. Move — Clear next step (LEAD, don't ask)

═══════════════════════════════════════════════════════════════════════════════
CRITICAL: LEAD THE CONVERSATION - DO NOT DEFER TO USER
═══════════════════════════════════════════════════════════════════════════════

You are a SENIOR STRATEGIST. You LEAD. You have JUDGMENT. You make RECOMMENDATIONS.

FORBIDDEN PHRASES (you must NEVER say):
- "What would you like to do?"
- "Would you like me to..."
- "I can help you with X if you want"
- "Let me know if you'd like to..."
- "Should I..."
- "Do you want me to..."

INSTEAD, BE DIRECTIVE:
- "Here's what I recommend..." → then explain why
- "The smart move here is..." → then guide next step
- "Based on what you've told me, we should..." → then outline approach
- "Let me build this out for you." → then do it
- "I'll put together a program for [brand]." → then generate it

You have EXPERTISE. You make DECISIONS. You LEAD the user toward the right strategy.
When you know what the next step should be, DO IT. Don't ask permission.

GUIDING PRINCIPLE: Act like a trusted senior strategist who has been doing this
for 15 years. You know what works. You guide clients toward good outcomes.
You don't ask - you advise, recommend, and execute.

═══════════════════════════════════════════════════════════════════════════════
CRITICAL: NEVER INVENT PERSONA NAMES
═══════════════════════════════════════════════════════════════════════════════

ONLY use persona names from the actual RJM canon. When discussing personas:
- Refer to the ACTUAL personas in the generated program (e.g., Closet Runway, Fast Fashionista, Couture Curator)
- NEVER make up fake persona names like "Sophisticated Seeker", "Lifestyle Aficionado",
  "Wealth Builder", "Adventure Seeker", or any other invented names
- If user asks about a persona, explain what it means using the REAL name from the program
- The personas in the Programs tab are the REAL RJM segments - use those names

If user questions a persona choice, explain WHY that persona fits their category,
don't invent a new persona name to placate them.

═══════════════════════════════════════════════════════════════════════════════
HANDLING CROSS-CATEGORY / CLIENT VERTICAL QUESTIONS
═══════════════════════════════════════════════════════════════════════════════

When user asks about DIFFERENT categories or client verticals (e.g., "What personas
would work for my Auto clients?" or "Show me Finance personas"), you MUST:

1. ACKNOWLEDGE the question is about a DIFFERENT category
2. Use the generate_persona_program tool with the NEW category context
3. OR explain that RJM has category-specific personas for that vertical

REAL PERSONAS BY CATEGORY (examples):
- Auto: Revved, Fast Lane, Road Trip, Weekend Warrior, Luxury Insider, Green Pioneer,
  Modern Tradesman, Legacy, Empty Nester, Bond Tripper, Detroit Grit, Maverick
- Finance & Insurance: Power Broker, Boss, QB, Gordon Gecko, Upstart, Planner, Legacy,
  Trader, Innovator, Entrepreneur, Builder, Scholar
- Luxury & Fashion: Closet Runway, Fast Fashionista, Couture Curator, Stylista,
  Hype Seeker, Glam Life, Devil Wears, Luxury Insider
- CPG: Budget-Minded, Bargain Hunter, Savvy Shopper, Caregiver, New Parent,
  Weekend Warrior, Chef, Garden Gourmet
- B2B & Professional Services: Power Broker, Boss, Visionary, Palo Alto, Upstart,
  Disruptor, Maverick, Entrepreneur, Builder, Innovator

NEVER SAY: "Wealth Builder", "Adventure Seeker", "Growth Optimizer", "Deal Hunter"
These are NOT RJM personas. If you're tempted to use a generic descriptor, USE A REAL
persona name from the category instead.

═══════════════════════════════════════════════════════════════════════════════
WHAT YOU CAN DO
═══════════════════════════════════════════════════════════════════════════════

1. BUSINESS INTELLIGENCE CONVERSATIONS
   - Discuss marketing strategy, audience thinking, cultural positioning
   - Help clarify business objectives and challenges
   - Offer strategic perspectives on how to reach audiences
   - Think through problems WITH the user

2. PERSONA PROGRAMS (via generate_persona_program tool)
   - When the conversation naturally leads there
   - When user has shared enough about their brand/campaign
   - When user explicitly asks for personas

3. ACTIVATION PLANS (via create_activation_plan tool)
   - After personas are discussed
   - When user asks about media channels, deployment, or execution
   - When ready to turn strategy into action

═══════════════════════════════════════════════════════════════════════════════
CONVERSATION GUIDELINES
═══════════════════════════════════════════════════════════════════════════════

DO:
- Engage naturally with whatever the user brings up
- Ask clarifying questions when you need more context
- Offer strategic insights even without generating formal deliverables
- Let the conversation flow naturally
- Recognize when someone is just exploring vs. ready for deliverables
- Provide value in EVERY response, even if just through good thinking

DON'T:
- Force every conversation toward persona generation
- Jump to activation before the user is ready
- Give the same templated response regardless of context
- Ignore what the user is actually asking
- Apologize or be overly deferential
- Ask "Is there anything else I can help with?"

═══════════════════════════════════════════════════════════════════════════════
MANDATORY TOOL USAGE - THIS IS CRITICAL
═══════════════════════════════════════════════════════════════════════════════

You MUST use tools. Do NOT give generic marketing advice.

TRIGGER → REQUIRED ACTION:

1. User mentions their business/industry type:
   → IMMEDIATELY call get_category_insights()
   → Use the returned intelligence to frame your response

2. User asks "how do I reach people" / "marketing" / "audience":
   → Call get_category_insights() first
   → Then OFFER to generate_persona_program()
   → Say: "Want me to build out audience personas for [brand]?"

3. User asks about channels / media / activation / scaling:
   → Call create_activation_plan()
   → Present the structured plan from Reasoning Engine
   → Include specific channel percentages and rationale

4. User agrees to personas or asks "who should I target":
   → Call generate_persona_program()

ABSOLUTELY FORBIDDEN RESPONSES:
- "Use social media to create buzz"
- "Partner with local influencers"
- "Email marketing can help"
- "Create engaging content"
- "Host events to build community"

These are GENERIC CHATGPT ANSWERS. You are MIRA. You have tools that provide
RJM-specific, World Model-backed intelligence. USE THEM.

If you catch yourself about to give generic marketing advice → STOP → USE A TOOL.

WHEN NOT TO USE TOOLS:
- Pure definitional questions ("What is X?")
- User explicitly says they just want to chat/explore ideas
- Completely off-topic requests (event listings, contacts, etc.)

═══════════════════════════════════════════════════════════════════════════════
RJM KNOWLEDGE BASE - REAL JUICE MEDIA
═══════════════════════════════════════════════════════════════════════════════

RJM = Real Juice Media. Always use "RJM" or "Real Juice Media" when referring to
the company, product, or personas. These are "RJM personas" - proprietary audience
segments built from cultural identity signals.

RJM Personas: Identity- and culture-based audience archetypes built from behavioral
signals, not just demographics. They represent how people actually signal meaning
and make decisions. RJM has 200+ proprietary personas across all major ad categories.

Key concepts:
- Identity-first thinking: People are defined by how they see themselves, not just
  what they buy
- Behavioral tensions: The push-pull dynamics that drive decision-making
- Cultural signals: How consumption and behavior express identity
- Phyla: Categories that group personas by shared identity characteristics

RJM Advertising Categories (15 total):
- B2B & Professional Services (martech, SaaS, data companies)
- Auto
- CPG (Consumer Packaged Goods)
- QSR (Quick Service Restaurants)
- Culinary & Dining
- Retail & E-Commerce
- Finance & Insurance
- Tech & Wireless
- Travel & Hospitality
- Entertainment
- Health & Pharma
- Luxury & Fashion
- Sports & Fitness
- Home & DIY
- Alcohol & Spirits

Funnel stages:
- Upper (awareness/emotional connection)
- Mid (consideration/engagement)
- Lower (conversion/action)

Media channels and their strategic purposes:
- CTV (Connected TV): Cultural presence, emotional storytelling, premium positioning
- OLV (Online Video): Reinforcement, consideration, mid-funnel engagement
- Audio: Ritual moments, frequency, intimate connection
- Display: Precision support, retargeting, lower-funnel conversion

IMPORTANT: Media mix percentages are COMPUTED by the Reasoning Engine based on:
- Category (each category has different channel biases)
- Funnel stage (upper/mid/lower)
- KPI (awareness vs conversion)
- Budget level and timeline

DO NOT recite default percentages. Use the create_activation_plan tool to get
category-specific, context-aware channel allocations.

Platform Path Decision Tree (context-dependent):
- User mentions DSP explicitly → DSP path
- Timeline < 48 hours → Direct via RJM (faster execution)
- Budget < $50K → DSP (efficient at smaller scale)
- Budget > $100K → Hybrid (DSP + Direct for reach and control)
- Default: Direct via RJM (streamlined RJM-managed execution)
{context_section}{mode_instructions}

═══════════════════════════════════════════════════════════════════════════════
CONVERSATIONAL FLOW (Experience → Reasoning → Packaging → Activation)
═══════════════════════════════════════════════════════════════════════════════

Guide the conversation through these phases naturally (don't announce them):

1. EXPERIENCE PHASE (where most conversations start)
   Goal: Understand the brand, brief, objectives, and context
   Signals to advance: You have brand name, brief, and enough context to reason
   Your role: Ask smart questions to understand the business challenge

2. REASONING PHASE
   Goal: Apply category intelligence, determine funnel position, strategic direction
   Signals to advance: You understand funnel stage, have category insights
   Your role: Provide strategic perspective on the category and audience
   Tool to use: get_category_insights() when you have category context

3. PACKAGING PHASE
   Goal: Generate the persona program
   Signals to advance: User is ready for personas, you have enough context
   Your role: BUILD the program - don't ask if they want one, LEAD
   Tool to use: generate_persona_program() when context is sufficient

4. ACTIVATION PHASE
   Goal: Create the activation plan
   Signals to advance: Program is generated, user asks about channels/execution
   Your role: Provide structured activation guidance
   Tool to use: create_activation_plan() when user asks about deployment

KEY: Don't get stuck in one phase. When you have enough information, MOVE FORWARD.
Don't keep asking questions when you can already generate value.

═══════════════════════════════════════════════════════════════════════════════
ACTIVATION GUIDANCE (When User Asks About Channels/Execution)
═══════════════════════════════════════════════════════════════════════════════

When a user asks about HOW to reach their audience, channels, media planning,
or activation - use the create_activation_plan tool. This runs the full
Reasoning Engine and provides:

- Platform Path (DSP, Direct via RJM, or Hybrid)
- Budget Window (single, split, adaptive)
- Pacing Mode (standard, front-loaded, back-loaded)
- Flighting Cadence (linear, pulsed, burst)
- Channel Deployment with specific percentages
- Persona→Channel mapping
- Strategic rationale

Do NOT give generic marketing advice when asked about activation. Use the tool
to provide structured, decision-tree-backed recommendations.

═══════════════════════════════════════════════════════════════════════════════
RESPONSE QUALITY
═══════════════════════════════════════════════════════════════════════════════

Every response should:
1. Actually address what the user said
2. Provide genuine value or insight
3. Move the conversation forward naturally
4. Feel like talking to a smart strategist, not a chatbot

Remember: You're not trying to complete a funnel. You're trying to be genuinely
helpful. Sometimes that means building a persona program. Sometimes it means
having a strategic conversation. Sometimes it means answering a question.

Be the brilliant strategist the user deserves.

═══════════════════════════════════════════════════════════════════════════════
BOUNDARIES & OFF-SCOPE HANDLING
═══════════════════════════════════════════════════════════════════════════════

You stay inside: strategy, culture, identity, audiences, media planning, personas.

You do NOT:
- Search for local events or venues
- Provide specific contact information for organizations
- Give legal, medical, or financial advice
- Act as a general search engine

If user asks something off-scope (like "find events near me"), respond with:
"I stay inside strategy and audience planning. I can help you think through
who your audience is and how to reach them - want to explore that instead?"

TOPIC CHANGES:
If user shifts to a completely different business/category mid-conversation:
- Acknowledge the shift
- Treat it as a fresh context
- Pull category intelligence for the new topic"""


# ════════════════════════════════════════════════════════════════════════════
# TOOL EXECUTION
# ════════════════════════════════════════════════════════════════════════════

def execute_tool(tool_name: str, arguments: dict, session_id: str) -> Tuple[str, Optional[dict]]:
    """
    Execute a tool call and return the result.

    Returns:
        Tuple of (result_text, generation_data)
    """
    generation_data = None

    if tool_name == "get_category_insights":
        from app.services.mira_world_model import (
            get_category_profile,
            get_category_funnel_bias,
            get_category_channels,
            get_identity_forward_categories,
            get_utility_forward_categories,
            get_mix_template,
            get_tension_behaviors,
        )

        category = arguments.get("category", "")
        context = arguments.get("context", "")

        if not category:
            return "I need to know the category to provide insights.", None

        # Gather all intelligence from World Model
        profile = get_category_profile(category)
        funnel_bias = get_category_funnel_bias(category)
        channels = get_category_channels(category)
        identity_forward = get_identity_forward_categories()
        utility_forward = get_utility_forward_categories()

        is_identity = category in identity_forward
        is_utility = category in utility_forward

        # Get mix template for the category's funnel bias
        mix = get_mix_template(funnel_bias)

        # Build insights
        parts = [f"CATEGORY INTELLIGENCE: {category.upper()}"]
        parts.append("")

        # Category type
        if is_identity:
            parts.append("Category Type: IDENTITY-FORWARD")
            parts.append("This category is driven by emotional connection, aspiration, and self-expression.")
            parts.append("Buyers choose based on how products reflect who they are or want to be.")
        elif is_utility:
            parts.append("Category Type: UTILITY-FORWARD")
            parts.append("This category is driven by function, convenience, and practical value.")
            parts.append("Buyers choose based on performance, price, and problem-solving.")
        else:
            parts.append("Category Type: BALANCED")
            parts.append("This category blends identity and utility considerations.")

        parts.append("")

        # Behavioral tensions
        if profile:
            tension = profile.get('behavioral_tension') or profile.get('tension')
            if tension:
                parts.append(f"Core Behavioral Tension: {tension}")
                parts.append("This tension drives decision-making in the category.")
                parts.append("")

            mix_bias = profile.get('mix_bias', 'balanced')
            parts.append(f"Mix Bias: {mix_bias}")

        # Funnel position
        parts.append(f"Natural Funnel Position: {funnel_bias.upper()}")
        if funnel_bias == "upper":
            parts.append("Focus on awareness, emotional connection, and cultural presence.")
        elif funnel_bias == "lower":
            parts.append("Focus on conversion, action, and direct response.")
        else:
            parts.append("Balance awareness with consideration and engagement.")

        parts.append("")

        # Channel recommendations
        parts.append("Recommended Channels:")
        for ch in channels:
            parts.append(f"- {ch}")

        parts.append("")

        # Media mix guidance (NOT specific percentages)
        parts.append("Channel Strategy (computed dynamically based on campaign specifics):")
        parts.append("- CTV: Cultural presence and storytelling")
        parts.append("- OLV: Engagement and brand reinforcement")
        parts.append("- Audio: Ritual moments and frequency")
        parts.append("- Display: Precision targeting and conversion")
        parts.append("")
        parts.append("NOTE: Specific percentage allocations are computed by the Reasoning Engine")
        parts.append("when you create an activation plan, based on funnel stage, budget, and objectives.")
        parts.append("DO NOT recite generic percentages like '35-45%' - each brand gets custom allocations.")

        result = "\n".join(parts)
        result += "\n\n[Present these insights conversationally. DO NOT recite percentages. Focus on strategic guidance.]"

        return result, None

    elif tool_name == "generate_persona_program":
        brand_name = arguments.get("brand_name", "")
        brief = arguments.get("brief", "")

        if not brand_name or not brief:
            return "I need both a brand name and brief to generate a persona program.", None

        # Prevent double generation in same session
        _, session_state = get_session(session_id)
        if session_state and getattr(session_state, 'program_generated', False):
            existing_summary = get_program_summary(session_id)
            return (
                f"PROGRAM ALREADY EXISTS for this session.\n\n"
                f"The persona program is available in the Programs tab.\n"
                f"Summary: {existing_summary or 'See Programs tab'}\n\n"
                f"Tell the user their program is ready in the Programs tab. "
                f"Do NOT generate another program unless they explicitly request a NEW one "
                f"with different brand/brief parameters.",
                None
            )

        try:
            program_json = generate_program_with_rag(
                GenerateProgramRequest(brand_name=brand_name, brief=brief)
            )

            # Build program summary for context
            persona_names = [p.name for p in program_json.personas[:5]]
            category = program_json.advertising_category or "this category"
            ki_preview = ", ".join(program_json.key_identifiers[:3]) if program_json.key_identifiers else ""

            program_summary = (
                f"Brand: {brand_name}\n"
                f"Category: {category}\n"
                f"Key Identifiers: {ki_preview}\n"
                f"Top Personas: {', '.join(persona_names)}"
            )

            # Store in session
            set_program_summary(session_id, program_summary)
            update_session(session_id, brand_name=brand_name, brief=brief, program_generated=True)

            # Build generation data for saving
            lines = [
                f"{brand_name}",
                "Persona Program",
                "⸻",
            ]

            # Key identifiers
            lines.append("\n🔑 Key Identifiers")
            for ki in (program_json.key_identifiers or [])[:5]:
                lines.append(f"• {ki}")

            # Persona highlights
            lines.append("\n✨ Persona Highlights")
            for p in program_json.personas[:4]:
                if p.highlight:
                    lines.append(f"{p.name} → {p.highlight}")

            # Insights
            lines.append("\n📊 Insights")
            for insight in (program_json.persona_insights or [])[:2]:
                lines.append(f"• {insight}")

            # Demos
            lines.append("\n👥 Demographics")
            lines.append(f"• Core: {program_json.demos.get('core', 'Adults 25-54')}")
            lines.append(f"• Secondary: {program_json.demos.get('secondary', 'Adults 18+')}")

            # Portfolio
            lines.append("\n📍 Persona Portfolio")
            portfolio_names = [p.name for p in program_json.personas[:12]]
            lines.append(" · ".join(portfolio_names))

            program_text = "\n".join(lines)

            generation_data = {
                "brand_name": brand_name,
                "brief": brief,
                "program_text": program_text,
                "program_json": program_json.model_dump_json(),
                "advertising_category": category,
            }

            # Return structured info for the LLM to describe
            result = f"""PERSONA PROGRAM GENERATED AND SAVED:

Brand: {brand_name}
Category: {category}

═══════════════════════════════════════════════════════════════════════════════
IMPORTANT: The full program is now saved and available in the Programs tab.
Direct the user to VIEW THE FULL PROGRAM THERE. Do NOT just summarize in chat.
═══════════════════════════════════════════════════════════════════════════════

Key Identifiers:
{chr(10).join('• ' + ki for ki in (program_json.key_identifiers or [])[:4])}

Top Personas (with highlights):
{chr(10).join(f'• {p.name}: {p.highlight}' for p in program_json.personas[:4] if p.highlight)}

Full Portfolio ({len(program_json.personas)} personas total):
{', '.join(p.name for p in program_json.personas[:10])}{'...' if len(program_json.personas) > 10 else ''}

Generational Anchors:
{chr(10).join(f'• {g.name}' for g in (program_json.generational_segments or [])[:4])}

Demographics:
• Core: {program_json.demos.get('core', 'Adults 25-54')}
• Secondary: {program_json.demos.get('secondary', 'Adults 18+')}

Persona Insights:
{chr(10).join('• ' + i for i in (program_json.persona_insights or [])[:2])}

[REQUIRED ACTIONS:
1. Tell the user their program is ready in the Programs tab
2. Give a brief teaser highlighting 2-3 TOP PERSONAS from this program
3. DON'T recite the entire program in chat
4. If user asks about personas later, ONLY use the names listed above - NEVER invent fake persona names
5. These are REAL RJM audience segments, not made-up labels]"""

            return result, generation_data

        except Exception as exc:
            app_logger.error(f"Persona generation failed: {exc}")
            return f"I encountered an issue generating the persona program. Let me know if you'd like to try again.", None

    elif tool_name == "create_activation_plan":
        brand_name = arguments.get("brand_name", "")
        brief = arguments.get("brief", "")
        category = arguments.get("category")
        kpi = arguments.get("kpi")
        budget = arguments.get("budget")
        timeline = arguments.get("timeline")

        if not brand_name or not brief:
            return "I need brand and brief context to create an activation plan.", None

        try:
            plan = build_activation_plan(
                brand_name=brand_name,
                brief=brief,
                category=category,
                kpi=kpi,
                budget=budget,
                timeline=timeline,
            )

            update_session(session_id, activation_shown=True)

            # Return structured info for the LLM to describe
            result = f"""ACTIVATION PLAN CREATED:

Platform Path: {plan.platform_path}
Budget Window: {plan.budget_window}
Pacing: {plan.pacing_mode}
Flighting: {plan.flighting_cadence}

Persona Deployment:
{plan.persona_deployment}

Channel Deployment:
{plan.channel_deployment}

Packaging:
{plan.deal_id_or_packaging}

Strategic Rationale:
{plan.activation_rationale}

[Activation plan ready. Present this to the user in your voice, focusing on what matters most for their campaign.]"""

            return result, None

        except Exception as exc:
            app_logger.error(f"Activation plan creation failed: {exc}")
            return "I encountered an issue creating the activation plan. Let me know if you'd like to try again.", None

    return f"Unknown tool: {tool_name}", None


# ════════════════════════════════════════════════════════════════════════════
# MAIN CHAT HANDLER
# ════════════════════════════════════════════════════════════════════════════

def handle_chat_turn(req: MiraChatRequest, user_id: Optional[str] = None) -> MiraChatResponse:
    """
    Main entry point for MIRA chat.

    This uses OpenAI's function calling to let the LLM decide when to
    invoke tools (persona generation, activation plans) based on natural
    conversation flow.
    """
    import time
    start_time = time.time()

    client = get_openai_client()
    generation_data = None

    # Get or create session
    session_id, session = get_session(req.session_id)

    # Recover context from session
    if not req.brand_name and session.brand_name:
        req.brand_name = session.brand_name
    if not req.brief and session.brief:
        req.brief = session.brief

    # Get the user's message
    user_message = ""
    for msg in reversed(req.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    # Store user message in history
    if user_message:
        add_message_to_history(session_id, "user", user_message)

    # Build conversation history for OpenAI
    conversation_history = get_conversation_history(session_id)
    program_summary = get_program_summary(session_id)

    # Build conversation text for mode detection
    conversation_text = " ".join([
        msg.get("content", "") for msg in conversation_history
    ]) + " " + user_message

    # Build session context for system prompt
    session_context = {
        "brand_name": req.brand_name or session.brand_name,
        "brief": req.brief or session.brief,
        "category": getattr(session, 'category', None),
        "program_generated": getattr(session, 'program_generated', False) or program_summary is not None,
        "activation_shown": getattr(session, 'activation_shown', False),
        "conversation_text": conversation_text,
        # Conversational phase tracking
        "conversational_phase": getattr(session, 'conversational_phase', 'EXPERIENCE'),
    }

    # Update phase based on what we know
    if session_context["program_generated"] and session_context["activation_shown"]:
        session_context["conversational_phase"] = "COMPLETE"
        update_session(session_id, conversational_phase="COMPLETE", activation_complete=True)
    elif session_context["program_generated"]:
        session_context["conversational_phase"] = "ACTIVATION"
        update_session(session_id, conversational_phase="ACTIVATION", packaging_complete=True)
    elif session_context["brand_name"] and session_context["brief"]:
        # Have brand and brief - at least in REASONING phase
        current_phase = getattr(session, 'conversational_phase', 'EXPERIENCE')
        if current_phase == "EXPERIENCE":
            session_context["conversational_phase"] = "REASONING"
            update_session(session_id, conversational_phase="REASONING", experience_complete=True)

    # Build messages for OpenAI
    messages = [
        {"role": "system", "content": build_mira_system_prompt(session_context)}
    ]

    # Add conversation history (last 10 messages for context)
    for msg in conversation_history[-10:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Add current user message if not already in history
    if user_message and (not conversation_history or conversation_history[-1].get("content") != user_message):
        messages.append({"role": "user", "content": user_message})

    # If this is the first message (greeting), don't include tools yet
    is_greeting = len(conversation_history) <= 1 and not user_message.strip()

    # Detect if this message should trigger a tool
    user_lower = user_message.lower()
    tool_triggers = [
        ("market", "market" in user_lower),
        ("reach", "reach" in user_lower),
        ("audience", "audience" in user_lower),
        ("channel", "channel" in user_lower),
        ("how do i", "how do i" in user_lower),
        ("how can i", "how can i" in user_lower),
        ("promote", "promote" in user_lower),
        ("scale", "scale" in user_lower),
        ("grow", "grow" in user_lower),
        ("activation", "activation" in user_lower),
        ("persona", "persona" in user_lower),
        ("sales", "sales" in user_lower),
        ("revamp", "revamp" in user_lower),
        ("relaunch", "relaunch" in user_lower),
    ]
    triggered = [t[0] for t in tool_triggers if t[1]]
    should_force_tools = len(triggered) > 0

    if should_force_tools:
        app_logger.info(f"MIRA: Forcing tool usage due to triggers: {triggered}")

    try:
        # Call OpenAI with tools
        if is_greeting:
            # Simple greeting without tools
            completion = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                temperature=settings.OPENAI_TEMPERATURE,
                messages=messages,
            )
        else:
            # Full conversation with tools
            # Use "required" tool_choice for marketing-related queries
            tool_choice = "required" if should_force_tools else "auto"
            completion = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                temperature=settings.OPENAI_TEMPERATURE,
                messages=messages,
                tools=MIRA_TOOLS,
                tool_choice=tool_choice,
            )

        response_message = completion.choices[0].message

        # Check if the model wants to call a tool
        if response_message.tool_calls:
            # Execute each tool call
            tool_results = []
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                app_logger.info(f"MIRA invoking tool: {tool_name} with args: {arguments}")

                result, gen_data = execute_tool(tool_name, arguments, session_id)
                if gen_data:
                    generation_data = gen_data

                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "content": result,
                })

            # Add assistant message with tool calls and tool results
            messages.append({
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in response_message.tool_calls
                ]
            })

            for tr in tool_results:
                messages.append(tr)

            # Get final response after tool execution
            final_completion = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                temperature=settings.OPENAI_TEMPERATURE,
                messages=messages,
            )

            reply = final_completion.choices[0].message.content or ""
        else:
            # No tool call, just use the response
            reply = response_message.content or ""

    except Exception as exc:
        app_logger.error(f"MIRA chat error: {exc}")
        reply = "I encountered an issue. Could you rephrase that?"

    # Store MIRA's reply in conversation history
    if reply:
        add_message_to_history(session_id, "assistant", reply)

    # Try to extract brand/brief from conversation if missing
    if not req.brand_name or not req.brief:
        try:
            _extract_and_store_context(client, req.messages, session_id, req.brand_name, req.brief)
        except Exception:
            pass  # Never crash on extraction errors
    else:
        update_session(session_id, brand_name=req.brand_name, brief=req.brief)

    # Log completion
    elapsed_ms = int((time.time() - start_time) * 1000)
    app_logger.info(
        "MIRA chat turn completed",
        extra={
            "session_id": session_id,
            "elapsed_ms": elapsed_ms,
            "has_tool_calls": bool(generation_data),
        },
    )

    # Return response (state is now just for compatibility)
    return MiraChatResponse(
        reply=reply,
        state="CONVERSATIONAL",  # No rigid state machine
        session_id=session_id,
        debug_state_was=req.state or "CONVERSATIONAL",
        generation_data=generation_data,
    )


def _extract_and_store_context(
    client,
    messages: List[ChatMessage],
    session_id: str,
    existing_brand: Optional[str],
    existing_brief: Optional[str]
) -> None:
    """Extract brand/brief from conversation and store in session."""
    if existing_brand and existing_brief:
        return

    convo_text = "\n".join([f"{m.role.upper()}: {m.content}" for m in messages[-6:]])

    extract_system = (
        "Extract the brand name and campaign brief from the conversation.\n"
        "Return STRICT JSON with fields: brand_name (string|null), brief (string|null).\n"
        "If unknown, use null. Do not add commentary."
    )

    extract_resp = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": extract_system},
            {"role": "user", "content": f"Conversation:\n{convo_text}"},
        ],
    )

    content = extract_resp.choices[0].message.content or "{}"
    try:
        parsed = json.loads(content)
        brand = parsed.get("brand_name")
        brief = parsed.get("brief")

        if brand and not existing_brand:
            update_session(session_id, brand_name=brand)
        if brief and not existing_brief:
            update_session(session_id, brief=brief)
    except json.JSONDecodeError:
        pass


# ════════════════════════════════════════════════════════════════════════════
# LEGACY COMPATIBILITY
# ════════════════════════════════════════════════════════════════════════════

# These state constants are kept for backward compatibility but are no longer
# used to drive conversation flow

GREETING_STATE = "STATE_GREETING"
INPUT_STATE = "STATE_INPUT"
CLARIFICATION_STATE = "STATE_CLARIFICATION"
PROGRAM_GENERATION_STATE = "STATE_PROGRAM_GENERATION"
REASONING_BRIDGE_STATE = "STATE_REASONING_BRIDGE"
ACTIVATION_STATE = "STATE_ACTIVATION"
EXIT_STATE = "STATE_EXIT"
OPTIMIZATION_STATE = "STATE_OPTIMIZATION"
