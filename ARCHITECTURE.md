# RJM-Backend Architecture Documentation

> **Version:** 1.0  
> **Last Updated:** January 2026  
> **Purpose:** Technical handoff documentation for the RJM Persona Program Generator and MIRA Chat System

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Core Components](#core-components)
4. [Data Flow](#data-flow)
5. [Persona Generation Pipeline](#persona-generation-pipeline)
6. [MIRA Chat System](#mira-chat-system)
7. [Persona Authority (Governance)](#persona-authority-governance)
8. [RJM Ingredient Canon](#rjm-ingredient-canon)
9. [API Endpoints](#api-endpoints)
10. [Database Schema](#database-schema)
11. [Configuration](#configuration)
12. [Key Design Decisions](#key-design-decisions)

---

## System Overview

The RJM-Backend is an AI-powered persona program generator that creates culturally-informed audience targeting programs for advertising campaigns. The system has two main interfaces:

1. **Direct Generator** (`/v1/rjm/generate`) - One-shot persona program generation from brand name and brief
2. **MIRA Chat** (`/v1/rjm/chat`) - Conversational AI interface for guided persona program creation

Both interfaces share the same underlying governance system (`PersonaAuthority`) to ensure consistent, high-quality output.

### Tech Stack

- **Framework:** FastAPI (Python 3.11+)
- **LLM:** OpenAI GPT-4 (configurable model)
- **Vector Store:** Pinecone (RAG retrieval)
- **Database:** Supabase (PostgreSQL)
- **Session Storage:** In-memory with TTL (60 min default)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                   │
│                    (Web Frontend / API Consumers)                           │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                      │
│                         (app/api/rjm/router.py)                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │ POST /generate   │  │ POST /chat       │  │ GET /generations         │   │
│  │ POST /sync       │  │ POST /transcribe │  │ GET/POST/DELETE /sessions│   │
│  └────────┬─────────┘  └────────┬─────────┘  └──────────────────────────┘   │
└───────────┼─────────────────────┼───────────────────────────────────────────┘
            │                     │
            ▼                     ▼
┌───────────────────────┐  ┌─────────────────────────────────────────────────┐
│   RAG PIPELINE        │  │              MIRA CHAT ENGINE                   │
│ (app/services/        │  │         (app/services/mira_chat.py)             │
│  rjm_rag.py)          │  │                                                 │
│                       │  │  ┌─────────────┐  ┌─────────────────────────┐   │
│ • Category Detection  │  │  │ Tool Calling│  │ Session Management      │   │
│ • Brand Analysis      │  │  │ (OpenAI)    │  │ (mira_session.py)       │   │
│ • Context Retrieval   │  │  └──────┬──────┘  └─────────────────────────┘   │
│ • Prompt Building     │  │         │                                       │
└───────────┬───────────┘  │         ▼                                       │
            │              │  ┌─────────────────────────────────────────────┐│
            │              │  │ Tools: generate_persona_program,            ││
            │              │  │        create_activation_plan,              ││
            │              │  │        get_category_insights,               ││
            │              │  │        research_brand                       ││
            │              │  └──────────────────────┬──────────────────────┘│
            │              └─────────────────────────┼───────────────────────┘
            │                                        │
            ▼                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PERSONA AUTHORITY                                   │
│                   (app/services/persona_authority.py)                       │
│                                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                 │
│  │ Validation     │  │ Selection      │  │ Governance     │                 │
│  │ - Category     │  │ - Highlights   │  │ - Rotation     │                 │
│  │ - Deprecation  │  │ - Insights     │  │ - Diversity    │                 │
│  │ - Canon check  │  │ - Portfolio    │  │ - Separation   │                 │
│  └────────────────┘  └────────────────┘  └────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RJM INGREDIENT CANON                                 │
│                (app/services/rjm_ingredient_canon.py)                       │
│                                                                             │
│  • Category → Persona Map (14 categories, 400+ personas)                    │
│  • Phylum Index (24 cultural phyla)                                         │
│  • Generational Segments (32 segments, 4 cohorts)                           │
│  • Multicultural Expressions (30 overlays)                                  │
│  • Local Culture DMA Segments (125 markets)                                 │
│  • Ad-Category Anchors (14 anchors)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SERVICES                                  │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ OpenAI API      │  │ Pinecone        │  │ Supabase        │              │
│  │ (LLM, STT)      │  │ (Vector Store)  │  │ (PostgreSQL)    │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. API Router (`app/api/rjm/router.py`)

The FastAPI router that exposes all endpoints. Key responsibilities:
- Request validation using Pydantic schemas
- Response formatting (program text generation from JSON)
- Database persistence for authenticated users
- Error handling and logging

### 2. RAG Pipeline (`app/services/rjm_rag.py`)

The Retrieval-Augmented Generation pipeline for persona program generation:

```python
# Key function: generate_program_with_rag(request)
# Flow:
# 1. Retrieve relevant RJM document chunks from Pinecone
# 2. Detect advertising category using LLM
# 3. Analyze brand context (audience type, persona guidance)
# 4. Build system prompt with category constraints
# 5. Call OpenAI to generate program JSON
# 6. Validate output through PersonaAuthority
# 7. Return structured ProgramJSON
```

### 3. MIRA Chat (`app/services/mira_chat.py`)

The conversational AI engine with tool-calling capabilities:

```python
# Key function: handle_chat_turn(request, user_id)
# Flow:
# 1. Get or create session
# 2. Build conversation context from history
# 3. Call OpenAI with tool definitions
# 4. Execute any tool calls (generate_persona_program, create_activation_plan, etc.)
# 5. Format response and update session state
# 6. Return reply with session_id
```

**Available Tools:**
- `generate_persona_program` - Create a persona program
- `create_activation_plan` - Create media activation recommendations
- `get_category_insights` - Get category intelligence
- `research_brand` - Web search for unknown brands

### 4. Persona Authority (`app/services/persona_authority.py`)

Centralized governance for all persona operations:

```python
class PersonaAuthority:
    """
    Single source of truth for:
    - Category-bounded persona selection
    - Deprecated persona rejection
    - Highlight/insight separation
    - Phylum diversity enforcement
    - Rotation pressure for freshness
    """
```

### 5. Ingredient Canon (`app/services/rjm_ingredient_canon.py`)

The complete reference data for the persona system:
- **CATEGORY_PERSONA_MAP**: 14 categories → persona lists
- **PHYLUM_INDEX**: 24 cultural phyla → persona lists
- **GENERATIONS_BY_COHORT**: Gen Z, Millennial, Gen X, Boomer segments
- **MULTICULTURAL_EXPRESSIONS**: 6 lineages → 30 expressions
- **LOCAL_CULTURE_SEGMENTS**: 125 DMA-based segments
- **ALL_ANCHORS**: 14 ad-category anchor segments

---

## Data Flow

### Direct Generation Flow

```
User Request (brand_name, brief)
         │
         ▼
┌─────────────────────────────────┐
│  1. infer_category_with_llm()  │  ← LLM determines advertising category
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│  2. analyze_brand_context()    │  ← LLM analyzes brand for persona guidance
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│  3. PersonaAuthority created   │  ← Governance rules initialized
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│  4. _build_rjm_context()       │  ← RAG retrieval from Pinecone
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│  5. OpenAI completion          │  ← Generate program JSON
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│  6. Validation & post-process  │  ← PersonaAuthority validates output
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│  7. Format program_text        │  ← Human-readable formatting
└────────────────┬────────────────┘
                 ▼
        Response (program_json, program_text)
```

### Chat Flow

```
User Message
     │
     ▼
┌─────────────────────────────────┐
│  1. Get/create session          │
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│  2. Build system prompt         │  ← Includes behavioral guidance
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│  3. OpenAI with tools           │  ← May invoke tools
└────────────────┬────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ▼                         ▼
┌──────────────┐      ┌──────────────────┐
│ Direct reply │      │ Tool execution   │
└──────────────┘      │ (persona program,│
                      │  activation, etc)│
                      └────────┬─────────┘
                               │
    ┌──────────────────────────┘
    ▼
┌─────────────────────────────────┐
│  4. Update session state        │
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│  5. Persist to database         │  ← If authenticated
└────────────────┬────────────────┘
                 ▼
        Response (reply, state, session_id)
```

---

## Persona Generation Pipeline

### Category Detection

Categories are detected using LLM reasoning (not keyword matching):

```python
def infer_category_with_llm(brand_name: str, brief: str) -> str:
    """
    LLM analyzes the brand and brief to determine the most appropriate
    advertising category from the 14 canonical categories.
    """
```

**Canonical Categories:**
1. CPG
2. Tech & Wireless
3. Culinary & Dining
4. Auto
5. Entertainment
6. Travel & Hospitality
7. Retail & E-Commerce
8. Health & Pharma
9. Finance & Insurance
10. Home & DIY
11. Luxury & Fashion
12. Sports & Fitness
13. Alcohol & Spirits
14. QSR

### Brand Context Analysis

Before persona selection, the system deeply analyzes the brand:

```python
def analyze_brand_context(brand_name: str, brief: str, category: str) -> Dict:
    """
    Returns:
    - audience_type: "consumer" | "civic" | "pet_service" | "fitness" | etc.
    - persona_guidance: LLM-generated guidance
    - prioritize_personas: List of personas to prioritize
    - avoid_personas: List of personas to avoid
    """
```

This solves the "sequencing problem" - understanding WHAT the brand is before deciding WHO the audience is.

### Persona Selection Rules

1. **Category Constraint**: Personas must be from the category's persona pool
2. **Deprecation Check**: No sunset/deprecated personas allowed
3. **Highlight Count**: Exactly 4 highlights (3 core + 1 generational)
4. **Insight Separation**: Insights MUST use different personas than highlights
5. **Phylum Diversity**: No more than 35% from a single phylum
6. **Rotation Pressure**: Recently used personas get lower selection weight

### Output Structure

```json
{
  "header": "Brand | Persona Framework",
  "advertising_category": "Category",
  "key_identifiers": ["4 noun phrases describing brand attributes"],
  "personas": [
    {"name": "Persona Name", "category": "...", "phylum": "...", "highlight": "..."}
  ],
  "generational_segments": [
    {"name": "Gen Z–Segment", "highlight": "..."}
  ],
  "persona_insights": ["2 insights with different personas than highlights"],
  "demos": {"core": "Adults 25-54", "secondary": "Adults 18+", "broad_demo": "..."},
  "activation_plan": ["4 canonical activation bullets"]
}
```

---

## MIRA Chat System

### Session Management

Sessions are stored in-memory with TTL expiration:

```python
@dataclass
class SessionState:
    brand_name: Optional[str]
    brief: Optional[str]
    category: Optional[str]
    current_state: str  # Behavioral state
    conversational_phase: str  # EXPERIENCE → REASONING → PACKAGING → ACTIVATION
    program_generated: bool
    conversation_history: List[Dict[str, str]]
    # ... more fields
```

### Tool Definitions

The chat uses OpenAI function calling:

```python
MIRA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_persona_program",
            "description": "...",
            "parameters": {
                "brand_name": "...",
                "brief": "...",
                "regenerate": "..."  # Allows re-generation
            }
        }
    },
    # create_activation_plan, get_category_insights, research_brand
]
```

### Conversation Persistence

For authenticated users, conversations are persisted to Supabase:

```python
await persist_chat_turn(
    session_id=session_id,
    user_id=user_id,
    user_message=user_message,
    assistant_reply=reply,
    state_before=state_before,
    state_after=state_after,
    brand_name=...,
    brief=...,
    category=...
)
```

---

## Persona Authority (Governance)

### Core Responsibilities

```python
class PersonaAuthority:
    def __init__(self, category, brand_name, brief):
        # Initialize category pool, anchors, context
        
    def validate_persona(self, name) -> Tuple[bool, str, Optional[str]]:
        # Returns (is_valid, canonical_name, rejection_reason)
        
    def select_highlights(self, available, count=4) -> List[str]:
        # Apply rotation pressure, ensure diversity
        
    def select_for_insights(self, available, count=2) -> List[str]:
        # MUST be different from highlights
        
    def build_portfolio(self, llm_personas, target_count=15) -> List[str]:
        # Validate, fill gaps, ensure diversity
```

### Rotation Pressure

To prevent "hot" personas from appearing too frequently:

```python
CATEGORY_HOT_PERSONAS = {
    "Travel & Hospitality": {"Romantic Voyager", "Retreat Seeker", "Island Hopper"},
    "CPG": {"Budget-Minded", "Bargain Hunter", "Savvy Shopper"},
    # ...
}

def get_rotation_weight(persona_name, category, recency_position):
    # Hot personas get 25-75% penalty
    # Recently used personas get additional penalty
```

### Highlight/Insight Separation

This is enforced as a HARD RULE:

```python
def select_for_insights(self, available, count=2, must_be_different=True):
    highlight_exclusion = set(self.context.selected_highlights)
    for name in available:
        if name in highlight_exclusion:
            continue  # BLOCKED
        # ...
```

---

## RJM Ingredient Canon

### Category → Persona Map

Each of the 14 categories has a curated list of personas:

```python
CATEGORY_PERSONA_MAP = {
    "CPG": [
        "Budget-Minded", "Bargain Hunter", "Savvy Shopper", "Planner",
        "Single Parent", "Caregiver", "New Parent", "Weekend Warrior",
        # ... 50+ personas
    ],
    "Travel & Hospitality": [
        "Romantic Voyager", "Retreat Seeker", "Island Hopper", "Backpacker",
        # ... 40+ personas
    ],
    # ...
}
```

### Phylum Index

Cultural lanes that ensure diversity:

```python
PHYLUM_INDEX = {
    "Sports & Competition": ["LeBron", "QB", "Lasso", "Basketball Junkie", ...],
    "Food & Culinary": ["Chef", "Pit Master", "Bourdain Mode", ...],
    "Style & Fashion": ["Stylista", "Fast Fashionista", "Sneakerhead", ...],
    # 24 phyla total
}
```

### Generational Segments

```python
GENERATIONS_BY_COHORT = {
    "Gen Z": ["Gen Z–Cloud Life", "Gen Z–Fast Culture", "Gen Z–Main Character Energy", ...],
    "Millennial": ["Millennial–Aware", "Millennial–Foodstagram", ...],
    "Gen X": ["Gen X–Crossfaded", "Gen X–Latchkey Life", ...],
    "Boomer": ["Boomer–Ambition Age", "Boomer–Camelot", ...],
}
```

### Deprecated Personas

These are blocked from all output:

```python
DEPRECATED_PERSONAS = {
    "Culture Maven",      # Replaced by Culture Connoisseur
    "Wellness Warrior",   # Replaced by Biohacker / Gym Obsessed
    "Soccer Mom",         # Use Sports Parent
    "Foodie",            # Too generic
    # ...
}
```

---

## API Endpoints

### POST `/v1/rjm/generate`

Generate a persona program directly.

**Request:**
```json
{
  "brand_name": "Example Brand",
  "brief": "Campaign brief describing objectives and audience"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "program_json": { /* ProgramJSON */ },
    "program_text": "Formatted human-readable program"
  }
}
```

### POST `/v1/rjm/chat`

Conversational interface with MIRA.

**Request:**
```json
{
  "messages": [{"role": "user", "content": "Help me create a persona program for Nike"}],
  "session_id": "optional-uuid",
  "state": "optional-state"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "reply": "MIRA's response",
    "state": "next_state",
    "session_id": "uuid"
  }
}
```

### POST `/v1/rjm/sync`

Sync RJM documents to Pinecone for RAG retrieval.

### POST `/v1/rjm/transcribe`

Convert audio to text for voice input.

### GET `/v1/rjm/generations`

List all persona generations for authenticated user.

### GET/POST/DELETE `/v1/rjm/sessions/*`

Manage chat session history.

---

## Database Schema

### `persona_generations` Table

```sql
CREATE TABLE persona_generations (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  brand_name TEXT NOT NULL,
  brief TEXT NOT NULL,
  program_text TEXT NOT NULL,
  program_json JSONB,
  advertising_category TEXT,
  source TEXT DEFAULT 'generator',  -- 'generator' or 'chat'
  session_id UUID,  -- If from chat
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### `chat_sessions` Table

```sql
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  title TEXT,
  brand_name TEXT,
  brief TEXT,
  category TEXT,
  current_state TEXT DEFAULT 'STATE_GREETING',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### `chat_messages` Table

```sql
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES chat_sessions(id),
  role TEXT NOT NULL,  -- 'user' or 'assistant'
  content TEXT NOT NULL,
  state_before TEXT,
  state_after TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Configuration

### Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.7

# Pinecone
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=rjm-index
PINECONE_ENVIRONMENT=us-east-1

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=...

# Application
LOG_LEVEL=INFO
SESSION_TTL_MINUTES=60
```

### Settings Module (`app/config/settings.py`)

```python
class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_TEMPERATURE: float = 0.7
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "rjm-index"
    # ...
```

---

## Key Design Decisions

### 1. LLM-First Category Detection

**Problem:** Keyword-based category detection failed for edge cases.

**Solution:** Use LLM to analyze brand and brief, determining category from context rather than pattern matching.

### 2. Brand Context Analysis Before Persona Selection

**Problem:** System was selecting personas before understanding the brand (the "sequencing problem").

**Solution:** `analyze_brand_context()` runs BEFORE persona selection to understand:
- Is this a civic campaign? → Prioritize civic personas, avoid shopping personas
- Is this a pet service? → Prioritize pet personas
- Is this fitness? → Prioritize fitness personas, avoid civic personas

### 3. PersonaAuthority as Single Source of Truth

**Problem:** Persona validation and selection logic was scattered across multiple files.

**Solution:** `PersonaAuthority` class centralizes ALL governance:
- Validation
- Selection
- Rotation
- Diversity
- Insight separation

### 4. Hard Separation of Highlights and Insights

**Problem:** LLM sometimes used the same persona in both highlights and insights.

**Solution:** `PersonaAuthority.context` tracks highlighted personas and BLOCKS them from insight selection.

### 5. Rotation Pressure for Freshness

**Problem:** Certain "hot" personas (Romantic Voyager, Budget-Minded) appeared too frequently.

**Solution:** 
- Global deques track recently used personas
- Hot personas get 25-75% selection penalty
- Travel & Hospitality limited to 1 hot persona per highlight set

### 6. Tool-Based Chat Architecture

**Problem:** Complex state machines were brittle and hard to maintain.

**Solution:** Let the LLM decide when to invoke tools (generate_persona_program, create_activation_plan) based on conversation context, with simple session state tracking.

---

## File Structure

```
app/
├── api/
│   └── rjm/
│       ├── router.py          # API endpoints
│       └── schemas.py         # Pydantic models
├── services/
│   ├── rjm_rag.py            # RAG pipeline
│   ├── rjm_ingredient_canon.py # Reference data
│   ├── persona_authority.py   # Governance
│   ├── mira_chat.py          # Chat engine
│   ├── mira_session.py       # Session management
│   ├── mira_activation.py    # Activation plans
│   ├── mira_reasoning_engine.py # Decision trees
│   ├── mira_world_model.py   # Category intelligence
│   ├── chat_persistence.py   # DB persistence
│   └── rjm_vector_store.py   # Pinecone client
├── config/
│   ├── settings.py           # Environment config
│   └── logger.py             # Logging setup
└── main.py                   # FastAPI app
```

---

## Contact

For questions about this architecture, contact the development team.
