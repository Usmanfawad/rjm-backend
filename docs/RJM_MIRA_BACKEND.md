# RJM MIRA Backend Documentation

## Overview

The RJM MIRA Backend implements the **RJM INGREDIENT CANON 11.26.25** specification, providing a complete persona packaging system for advertising campaigns.

## Architecture

### Core Components

1. **`rjm_ingredient_canon.py`** - The authoritative source for all RJM data:
   - Category → Persona Map (13 categories)
   - Phylum Index (22 phyla)
   - Ad-Category Anchor Segments (14 anchors)
   - Generations (32 segments across 4 cohorts)
   - Multicultural Expressions (30 expressions across 6 lineages)
   - Local Culture DMA Segments (125 markets)

2. **`rjm_rag.py`** - RAG pipeline + OpenAI generation
3. **`router.py`** - API endpoints and output formatting
4. **`category_mapping.py`** - Backward-compatible wrapper

---

## API Endpoints

### POST `/v1/rjm/generate`

Generate a persona program from a brand name and brief.

**Request:**
```json
{
  "brand_name": "L'Oréal",
  "brief": "Beauty brand focused on ritual, self-expression, and confidence."
}
```

**Response:**
```json
{
  "program_json": {
    "header": "L'Oréal | Persona Framework",
    "advertising_category": "Luxury & Fashion",
    "key_identifiers": ["...", "...", "...", "..."],
    "personas": [...],
    "generational_segments": ["Gen Z–...", "Millennial–...", "Gen X–...", "Boomer–..."],
    "persona_insights": ["...", "..."],
    "demos": {"core": "Adults 25-54", "secondary": "Adults 18+", "broad_demo": "Adults 18-64"},
    "activation_plan": [...]
  },
  "program_text": "..."
}
```

---

## Key Features

### 1. Category-First Selection
The system infers the advertising category from the brand name and brief, then selects personas from the category-mapped pool first.

### 2. Dual-Anchor Support
Brands that span multiple categories (e.g., L'Oréal = CPG + Luxury & Fashion) receive dual anchors:
- `RJM CPG`
- `RJM Luxury & Fashion`

### 3. Phylum Diversity
Personas are diversified across phyla to ensure cultural dimensionality:
- Minimum 3 distinct phyla
- Maximum 30% dominance from any single phylum

### 4. Generational Segments (32 total)
Every program includes 4 generational anchors, one from each cohort:
- **Gen Z (8):** Cloud Life, Fast Culture, Main Character Energy, SelfTok, Gossip, Alt Hustle, Cause Identity, Prompted
- **Millennial (8):** Aware, Foodstagram, Growth-Minded, Spin Juice, Startup Nation, Throwback, Wanderlust, Vibing
- **Gen X (8):** "Brand" New World, Crossfaded, Free World, Isn't It Ironic?, Latchkey Life, Mixtape Society, Pop Language, Teen Spirit
- **Boomer (8):** Ambition Age, Camelot, Counterculture, The Living Room, Marching Forward, Shifting Roles, Suburbia, Universal Soundtrack

### 5. Multicultural Expressions (30 total)
Applied when the brief targets specific cultural lineages:
- Black American (5)
- Latino / Hispanic (5)
- AAPI (5)
- South Asian / Desi (5)
- MENA (5)
- Hybrid / Global (5)

### 6. Local Culture DMA Segments (125 markets)
Applied only when the brief explicitly targets DMA/state/city geography.

### 7. Rotation Logic
In-memory tracking prevents repetition of:
- Core personas (120 item window)
- Generational segments (40 item window)

---

## Output Format

### Section Order (Emoji Law)
1. 🔑 Key Identifiers (4-5 bullets)
2. ✨ Persona Highlights (4 lines: 3 core + 1 generational)
3. 📊 Persona Insights (2 bullets with percentage bands)
4. 👥 Demos (Core + Secondary + optional Broad)
5. 📍 Persona Portfolio (~20 entries)
6. 🧭 Activation Plan (4 canonical bullets)
7. 📍 Local Strategy (optional, DMA briefs only)
8. 🌍 Multicultural Layer (optional, when detected)

### Persona Portfolio Structure
```
[15 Core Personas] · [1-2 Category Anchors] · [4 Generational Segments]
```

### Persona Insights Format
- High band: 33-42%
- Low band: 21-32%
- Minimum 5 points separation
- Persona nickname in quotes at end

---

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=rjm-docs

# Optional
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
DATABASE_URL=sqlite+aiosqlite:///./local.db
```

---

## Dual-Anchor Brands

The following brands automatically receive dual anchors:

| Brand | Categories |
|-------|------------|
| L'Oréal | CPG + Luxury & Fashion |
| Estée Lauder | CPG + Luxury & Fashion |
| Nike | Sports & Fitness + Retail & E-Commerce |
| Adidas | Sports & Fitness + Retail & E-Commerce |
| Apple | Tech & Wireless + Luxury & Fashion |
| Amazon | Retail & E-Commerce + Tech & Wireless |
| Disney | Entertainment + Travel & Hospitality |
| Marriott | Travel & Hospitality + Luxury & Fashion |

---

## Version History

- **11.26.25** - RJM Ingredient Canon integration
  - Consolidated all ingredient data into single source
  - Added 32 generational segments with descriptions
  - Added 30 multicultural expressions
  - Added 125 DMA local culture segments
  - Implemented dual-anchor logic for multi-category brands
  - Fixed L'Oréal dual anchor (CPG + Luxury & Fashion)
