"""
RJM INGREDIENT CANON 11.26.25
The Complete Ingredient System for Persona Packaging

This module consolidates all product reference points:
- Category → Persona Map (Section I)
- Phylum Index (Section II)
- Ad-Category Anchor Segments (Section III)
- Specialty Products (Section IV):
  - Generations (32)
  - Multicultural Expressions (30)
  - Local Culture DMA Segments (125)
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Sequence, Set, Tuple

from app.config.logger import app_logger


# ════════════════════════════════════════════════════════════════════════════
# SECTION I — CATEGORY → PERSONA MAP
# Primary Selector — The First Layer of Every Persona Program
# ════════════════════════════════════════════════════════════════════════════

CATEGORY_PERSONA_MAP: Dict[str, List[str]] = {
    "CPG": [
        "Budget-Minded", "Bargain Hunter", "Savvy Shopper", "Planner", "Single Parent", "Caregiver",
        "New Parent", "Weekend Warrior", "Gifter", "Road Trip", "Chef", "Garden Gourmet", "Self-Love",
        "Optimist", "Alchemist", "Impulse Buyer", "Cultural Harmonist", "Legacy", "The Fixer", "Retiree", "Julia",
        "Oprah", "Stylista", "Romantic Voyager", "Southern Hospitality", "Empty Nester", "Point Warrior",
        "Design Maven", "Clean Eats", "Detox", "Stretch", "Hydrating", "Step Counter", "Sideways",
        "Sweet Tooth", "Gift Wrap", "Family Table", "Sunday Reset", "Morning Commute", "After Hours",
        "Host", "Holiday Table", "Trailblazer", "Faith", "Believer", "Off the Grid", "Neighborhood Watch",
        "Volunteer", "PTA", "Pack Leader", "Cat Person", "Dog Parent", "Rescuer",
    ],
    "Tech & Wireless": [
        "Techie", "Influencer", "Gamer", "Visionary", "Digital Nomad", "Power Broker", "Luxury Insider",
        "Creator", "Maverick", "Timothee", "Fast Fashionista", "Closet Runway", "Sneakerhead", "Stylista",
        "Hype Seeker", "Boss", "Palo Alto", "Upstart", "Prime Mover", "Hollywood Hills", "Bond Tripper",
        "Fixer", "Architect", "Disruptor", "Socialite", "Madonna", "Beyoncé", "Sinatra", "Matador", "Glam Life",
        "Rhythm Nation", "Optimist", "Culture Connoisseur", "Innovator", "Builder", "Entrepreneur", "Trader",
        "Reader", "Writer", "Scholar", "Modern Monk", "Trailblazer", "Speedrunner", "Streamer Mode",
        "Controller Drop", "LAN Party", "Modder", "Quest Log", "AFK Life", "Vinyl", "EDM Afterlife",
        "Rap Caviar", "Stargazer", "Late Checkout", "Morning Commute", "Payday", "Journey",
    ],
    "Culinary & Dining": [
        "Taco Run", "Breakfast Burrito", "Pizza Night", "Sweet Tooth", "Cold Brew", "Sideways",
        "Holiday Table", "Family Table", "Gift Wrap", "Host", "Night In", "Cheers", "Big Date", "Holiday Hang",
        "Faith", "Believer", "Sanctuary", "Sunday Reset", "Morning Commute", "After Hours", "First Date",
        "Late Checkout", "Ribeye", "Trailblazer", "Country Mile", "Garden Gourmet", "Food Truckin'",
        "Takeout Guru", "Pit Master", "Michelin Chaser", "Bourdain Mode", "Caffeine Fiend", "Nightcapper",
        "Social Butterfly", "Austin Unplugged", "Romantic Voyager", "Miami Vibe", "Gatsby", "Bourbon Streeter",
        "Design Maven", "Chef", "Adrenaline Junkie", "Influencer", "Night Owl", "Sports Parent", "Southern Hospitality",
    ],
    "Auto": [
        "Revved", "Fast Lane", "Road Trip", "Planner", "Weekend Warrior", "Tailgater", "Sports Parent",
        "Luxury Insider", "Green Pioneer", "Modern Tradesman", "Legacy", "Empty Nester", "Bond Tripper",
        "Malibu Nomad", "Upstart", "Boss", "Power Broker", "Fantasy GM", "Disruptor", "Vegas High Roller",
        "Detroit Grit", "Visionary", "Matador", "Yellowstoner", "Glam Life", "Maverick", "Campfire",
        "Country Club", "Tiger", "Morning Stroll", "Neighborhood Watch", "Main Street", "Mayor", "PTA",
        "Hometown Hero", "Red Rockin'", "Motowner", "Beats", "Kendrick", "Soundcheck", "Festivalgoer",
        "Rest Stop", "Mentor", "Luke", "Seinfeld",
    ],
    "Entertainment": [
        "Binge Watcher", "Creator", "Gamer", "Influencer", "Night Owl", "Cultural Enthusiast", "Social Butterfly",
        "Digital Nomad", "Timothee", "Madonna", "Beyoncé", "Tarantino", "Old Soul", "Sneakerhead", "Beats",
        "Backpacker", "Closet Runway", "Single Parent", "PreChecker", "Weekend Warrior", "Gatsby",
        "Coachella Mind", "Yo! MTV", "Rap Caviar", "Red Rockin'", "Swiftie", "Festivalgoer", "Soundcheck",
        "Seinfeld", "Vinyl", "Backstage Pass", "Performer", "Mentor", "Luke", "Kendrick", "Writer",
        "Reader", "Night In", "After Hours", "Morning Commute", "Family Table", "Cheers", "Big Date",
        "Holiday Hang", "Streamer Mode",
    ],
    "Travel & Hospitality": [
        "Romantic Voyager", "Retreat Seeker", "Island Hopper", "Backpacker", "PreChecker",
        "Malibu Nomad", "Free Thinker", "Southern Hospitality", "Late Checkout", "First Date",
        "Holiday Hang", "Reel Life", "Nature Lover", "Stargazer", "Trailblazer", "Off the Grid", "Country Mile",
        "Backstage Pass", "Vinyl", "EDM Afterlife", "Rap Caviar", "Coachella Mind", "Faith", "Believer",
        "Pilgrim", "Sanctuary", "Journey", "Sunday Reset", "After Hours", "Family Table", "Host",
        "Pack Leader", "Dog Parent", "Cat Person", "Rescuer", "Empty Nester", "Weekend Warrior",
        "Road Trip", "Beach Bum", "Bourdain Mode", "Planner", "Digital Nomad", "Bond Tripper", "Miami Vibe",
        "Gatsby", "Hemingway", "Old Soul", "Social Architect", "Adrenaline Junkie", "Luxury Insider",
    ],
    "Retail & E-Commerce": [
        "Bargain Hunter", "Budget-Minded", "Savvy Shopper", "Planner", "Impulse Buyer", "Empty Nester",
        "Single Parent", "Split Family", "Modern Tradesman", "Point Warrior", "Gifter", "Sneakerhead",
        "Closet Runway", "Stylista", "Fast Fashionista", "Vintage Stylist", "Collector", "Design Maven",
        "Hype Seeker", "Techie", "Digital Nomad", "Influencer", "Social Butterfly", "Big Date", "Gift Wrap",
        "Holiday Table", "Ribeye", "Sideways", "Trailblazer", "Streetwear Soul", "Country Mile", "Vinyl",
        "Backstage Pass", "Dog Parent", "Cat Person", "Rescuer", "Pack Leader", "Faith", "Believer",
        "Off the Grid", "Payday", "Sunday Reset", "Morning Commute", "After Hours", "Family Table",
        "Holiday Hang", "Host",
    ],
    "Health & Pharma": [
        "Self-Love", "The Alchemist", "Gym Obsessed", "Sculpt", "Biohacker", "Caregiver", "Retiree",
        "Empty Nester", "Legacy", "Single Parent", "Planner", "Weekend Warrior", "Clean Eats", "Detox",
        "Stretch", "Step Counter", "Hydrating", "Morning Stroll", "Sanctuary", "Believer", "Faith", "Journey",
        "Nature Lover", "Country Mile", "Sunday Reset", "Morning Commute", "After Hours", "Night In", "Host",
        "Hiker", "Campfire", "Trailblazer", "Modern Monk", "Golden Age", "Optimist", "Old Soul", "Oprah",
    ],
    "Finance & Insurance": [
        "Power Broker", "Boss", "QB", "Gordon Gecko", "Upstart", "Potomac Power", "Palo Alto",
        "Planner", "Legacy", "Point Warrior", "Prime Mover", "Crypto Bro", "Disruptor", "LeBron", "Matador",
        "Visionary", "Techie", "Empty Nester", "Single Parent", "Golden Age", "Trader", "Innovator",
        "Entrepreneur", "Builder", "Scholar", "Reader", "Writer", "Modern Monk", "Pilgrim", "Journey",
        "Sanctuary", "Faith", "Believer", "Payday", "First Date", "Late Checkout", "Morning Commute", "After Hours",
        "Family Table", "Mentor", "Luke", "Hometown Hero", "Sideways", "Trailblazer", "Sunday Reset",
    ],
    "Home & DIY": [
        "Modern Tradesman", "Fixer", "Legacy", "Architect", "Renovator", "Design Maven", "Garden Gourmet",
        "Boss", "Empty Nester", "Planner", "Budget-Minded", "Collector", "Green Pioneer",
        "Single Parent", "Old Soul", "Nashville Dream", "Builder", "Host", "Family Table", "Holiday Table",
        "Believer", "Holiday Hang", "Gift Wrap", "After Hours", "Morning Commute", "Sunday Reset",
        "Off the Grid", "Nature Lover", "Trailblazer", "Stargazer", "Dog Parent", "Cat Person", "Rescuer",
        "Pack Leader", "Reader", "Writer", "Innovator", "Ribeye", "Sideways", "First Date", "Payday", "Trader",
    ],
    "Luxury & Fashion": [
        "Closet Runway", "Fast Fashionista", "Couture Curator", "Stylista", "Hype Seeker", "Glam Life",
        "Sneakerhead", "Collector", "Luxury Insider", "Devil Wears", "Culture Connoisseur", "Sideways",
        "First Date", "Big Date", "Cheers", "Holiday Table", "Holiday Hang", "Gift Wrap", "Vinyl", "Backstage Pass",
        "Hometown Hero", "Trailblazer", "Performer", "Morning Commute", "After Hours", "Lulu",
        "Swiftie", "Red Rockin'", "Seinfeld", "Night In", "Host", "Best in Show", "Miami Vibe", "Jenny from the Block",
        "Hampton's Charm", "Socialite", "Hollywood Hills", "Design Maven", "Boss", "Influencer",
    ],
    "Sports & Fitness": [
        "Gym Obsessed", "Elite Competitor", "Sculpt", "Sports Parent", "Weekend Warrior", "Fantasy GM",
        "Rackets", "Basketball Junkie", "Gamer", "Coach", "QB", "LeBron", "Biohacker", "Prime Mover",
        "Game Day", "Morning Stroll", "Tiger", "Campfire", "Hiker", "Country Mile", "Trailblazer", "Stargazer",
        "Nature Lover", "Off the Grid", "Step Counter", "Stretch", "Hydrating", "Detox", "Clean Eats", "Sunday Reset",
        "After Hours", "Morning Commute", "Family Table", "Host", "Pack Leader", "Dog Parent", "Cat Person", "Rescuer",
        "Petfluencer", "Best in Show", "Fast Lane", "Sneakerhead", "Matador", "Boss", "Power Broker", "Lasso", "Adrenaline Junkie",
    ],
    "Alcohol & Spirits": [
        "Nightcapper", "Bourbon Streeter", "Beer League", "Pit Master", "Tailgater", "Bartender", "Chef",
        "Social Butterfly", "Night Owl", "Miami Vibe", "Vegas High Roller", "Bond Tripper", "Influencer",
        "Southern Hospitality", "Bourdain Mode", "Food Truckin'", "Glam Life", "Gatsby", "Old Soul",
        "Hemingway", "Rhythm Nation", "Cheers", "Night In", "After Hours", "Late Checkout", "First Date",
        "Big Date", "Holiday Hang", "Holiday Table", "Host", "Family Table", "Sunday Reset", "Morning Commute",
        "Payday", "Sideways", "Ribeye", "Trailblazer", "Performer", "Backstage Pass", "Vinyl",
        "Rap Caviar", "EDM Afterlife", "Coachella Mind", "Red Rockin'", "Swiftie", "Gift Wrap", "Petfluencer",
        "Pawrent", "Best in Show",
    ],
    "QSR": [
        "Takeout Guru", "Food Truckin'", "Caffeine Fiend", "Gamer", "Sneakerhead", "Night Owl",
        "Beer League", "Single Parent", "Southern Hospitality", "Road Trip", "Bargain Hunter",
        "Budget-Minded", "Impulse Buyer", "Backpacker", "Digital Nomad", "Fantasy GM", "Tailgater",
        "Sports Parent", "Taco Run", "Extra Fries", "Sauce", "Burger Fiend", "Pizza Night", "Sweet Tooth",
        "Sides Only", "Cold Brew", "Breakfast Burrito", "Clean Eats", "Detox", "Stretch", "Step Counter",
        "Neighborhood Watch", "Block Party", "Main Street", "Volunteer", "The Mayor", "PTA", "Red Rockin'",
        "Swiftie", "Coachella Mind", "Game Day", "Midnight Run",
    ],
}


# ════════════════════════════════════════════════════════════════════════════
# SECTION II — PHYLUM INDEX (SECONDARY SELECTOR)
# Ensures persona diversity, cultural dimensionality, and prevents over-clustering
# ════════════════════════════════════════════════════════════════════════════

PHYLUM_PERSONA_MAP: Dict[str, List[str]] = {
    "Sports & Competition": [
        "LeBron", "QB", "Lasso", "Basketball Junkie", "Sculpt", "Sports Parent", "Sports Enthusiast",
        "Beer League", "Tailgater", "Elite Competitor", "Fantasy GM", "Rackets", "Adrenaline Junkie", "Tiger",
    ],
    "Gaming & Interactive": [
        "Gamer", "LAN Party", "Speedrunner", "AFK Life", "Streamer Mode", "Modder", "Controller Drop", "Quest Log",
    ],
    "Food & Culinary": [
        "Chef", "Pit Master", "Bourdain Mode", "Michelin Chaser", "Garden Gourmet", "Nightcapper", "Takeout Guru",
        "Food Truckin'", "Caffeine Fiend", "Bartender", "Taco Run", "Extra Fries", "Sauce", "Midnight Run",
        "Burger Fiend", "Breakfast Burrito", "Sweet Tooth", "Sides Only", "Sideways", "Cold Brew", "Pizza Night",
    ],
    "Wellness & Body Culture": [
        "Biohacker", "Optimist", "Gym Obsessed", "Detox", "Stretching", "Stretch", "Hydrating", "Morning Stroll",
        "Clean Eats", "Step Counter", "Self-Love",
    ],
    "Style & Fashion": [
        "Stylista", "Fast Fashionista", "Closet Runway", "Vintage Stylist", "Sneakerhead", "Maven", "Glam Life",
        "Couture Curator", "Devil Wears", "Streetwear Soul", "Hype Seeker",
    ],
    "Luxury & Affluence": [
        "Luxury Insider", "Hollywood Hills", "Miami Vibe", "Socialite", "Gatsby", "Hepburn", "Hamptons Charm", "Hampton's Charm",
        "Vegas High Roller", "Country Club",
    ],
    "Work & Hustle": [
        "Prime Mover", "Upstart", "Power Broker", "The Boss", "Boss", "Disruptor", "Maverick", "Matador",
        "Gordon Gekko", "Gordon Gecko", "Trader", "Entrepreneur", "Builder",
    ],
    "Creative & Arts": [
        "Collector", "Design Maven", "Culture Connoisseur", "Julia", "Madonna", "Architect", "Coachella Mind",
        "Performer", "Reader", "Writer",
    ],
    "Music & Nightlife": [
        "Rhythm Nation", "Night Owl", "Social Butterfly", "ATL", "Jenny from the Block", "Nashville Dream",
        "Beyoncé", "Bourbon Streeter", "Beats", "Swiftie", "Kendrick", "Motown Love", "Red Rockin'", "Red Rocking",
        "Soundcheck", "Block Party", "Yo! MTV", "Rap Caviar", "EDM Afterlife", "Country Mile", "Vinyl", "Backstage Pass",
        "Festivalgoer", "Motowner",
    ],
    "Travel & Exploration": [
        "Romantic Voyager", "Retreat Seeker", "Island Hopper", "Backpacker", "Digital Nomad", "Road Trip",
        "Bond Tripper", "Weekend Warrior", "Yellowstoner", "Beach Bum", "Pre Checker", "PreChecker", "Rest Stop",
    ],
    "Tech & Innovation": [
        "Techie", "Visionary", "Palo Alto", "Crypto Bro", "Renovator", "Digital Nomad", "Ribeye", "Innovator",
    ],
    "Family & Caregiving": [
        "Single Parent", "New Parent", "Caregiver", "Empty Nester", "Legacy", "Retiree", "Host", "Split Family",
    ],
    "Community & Local Pride": [
        "Southern Hospitality", "Boston Strong", "Detroit Grit", "Chicago Summer", "Austin Unplugged",
        "Rocky Mountain High", "Cultural Harmonist", "Social Architect", "Main Street", "Neighborhood Watch",
        "Hometown Hero", "Volunteer",
    ],
    "Pop Culture & Media Junkies": [
        "Binge Watcher", "Influencer", "Creator", "Timothée", "Timothee", "Seinfeld", "Tarantino", "Cultural Enthusiast",
    ],
    "Automotive & Car Culture": [
        "Revved", "Fast Lane", "Modern Tradesman",
    ],
    "Civic & Politics": [
        "Potomac Power", "Oprah", "Mayor", "The Mayor", "PTA",
    ],
    "Education & Growth": [
        "Coach", "Planner", "Self Love", "Fixer", "The Fixer", "Mentor", "Morning Stroll", "Scholar", "Luke",
    ],
    "Shopper Mindset": [
        "Savvy Shopper", "Gifter", "Impulse Buyer", "Bargain Hunter", "Point Warrior", "Budget Minded", "Budget-Minded", "Gift Wrap",
    ],
    "Spiritual & Philosophical": [
        "Old Soul", "Alchemist", "The Alchemist", "Green Pioneer", "Hemingway", "Malibu Nomad", "Golden Age", "Sinatra",
        "Believer", "Pilgrim", "Modern Monk", "Sanctuary", "Faith", "Free Thinker", "Journey",
    ],
    "Outdoors & Nature": [
        "Hiker", "Campfire", "Tiger", "Country Club", "Morning Stroll", "Trailblazer", "Off The Grid", "Off the Grid", "Stargazer", "Reel Life", "Nature Lover",
    ],
    "Pets & Companionship": [
        "Dog Parent", "Cat Person", "Rescuer", "Pack Leader", "Petfluencer", "Pawrent", "Best in Show", "Lulu",
    ],
    "Moments & Holidays": [
        "Holiday Table", "Cheers", "Big Date", "Night In", "Game Day", "Payday", "Sunday Reset", "First Date",
        "Late Checkout", "Morning Commute", "After Hours", "Family Table", "Holiday Hang", "Pizza Night",
    ],
}

# Build reverse lookup: persona name → phylum
PERSONA_TO_PHYLUM: Dict[str, str] = {}
for _phylum, _personas in PHYLUM_PERSONA_MAP.items():
    for _persona in _personas:
        PERSONA_TO_PHYLUM[_persona] = _phylum


# ════════════════════════════════════════════════════════════════════════════
# SECTION III — AD-CATEGORY ANCHOR SEGMENTS (14 canonical anchors)
# Always included in every persona program. Do NOT require write-ups.
# ════════════════════════════════════════════════════════════════════════════

AD_CATEGORY_ANCHORS: Dict[str, List[str]] = {
    "Auto": ["RJM Auto"],
    "QSR": ["RJM QSR", "RJM Culinary & Dining"],  # QSR gets dual anchor per spec
    "Culinary & Dining": ["RJM Culinary & Dining"],
    "Retail & E-Commerce": ["RJM Retail & E-Commerce"],
    "CPG": ["RJM CPG"],
    "Finance & Insurance": ["RJM Finance & Insurance"],
    "Tech & Wireless": ["RJM Tech & Wireless"],
    "Entertainment": ["RJM Entertainment & Media"],
    "Travel & Hospitality": ["RJM Travel & Hospitality"],
    "Health & Pharma": ["RJM Pharma & Wellness"],
    "Home & DIY": ["RJM Home & DIY"],
    "Luxury & Fashion": ["RJM Luxury & Fashion"],
    "Alcohol & Spirits": ["RJM Spirits & Alcohol"],
    "Sports & Fitness": ["RJM Sports & Fitness"],
}

# All 14 anchor names for reference
ALL_ANCHORS: List[str] = [
    "RJM Auto",
    "RJM QSR",
    "RJM Culinary & Dining",
    "RJM Retail & E-Commerce",
    "RJM CPG",
    "RJM Finance & Insurance",
    "RJM Tech & Wireless",
    "RJM Entertainment & Media",
    "RJM Travel & Hospitality",
    "RJM Pharma & Wellness",
    "RJM Home & DIY",
    "RJM Luxury & Fashion",
    "RJM Spirits & Alcohol",
    "RJM Sports & Fitness",
]


# ════════════════════════════════════════════════════════════════════════════
# SECTION IV — SPECIALTY PRODUCTS
# Contextual Layers Applied Based on Cohort, Culture, and Geography
# ════════════════════════════════════════════════════════════════════════════

# ────────────────────────────────────────────────────────────────────────────
# A. GENERATIONS (32 total)
# Age-driven worldview layers applied to every program.
# Every persona program includes four generational anchors — one for each cohort.
# ────────────────────────────────────────────────────────────────────────────

GENERATIONS: Dict[str, Dict[str, str]] = {
    # GEN Z (8)
    "Gen Z–Cloud Life": "Curated for a generation that embodies life lived online — where platforms, streams, and feeds aren't tools but the atmosphere itself.",
    "Gen Z–Fast Culture": "Curated for a generation that embodies the churn of trends — aesthetics, food, and lifestyles flipped fast, adopted and discarded at warp speed.",
    "Gen Z–Main Character Energy": "Curated for a generation that embodies life as the star of their own story — everyday moments framed as performance, style, and shareable identity.",
    "Gen Z–SelfTok": "Curated for a generation that embodies therapy-talk and self-growth as cultural currency — where humor, rituals, and self-expression turn healing into content.",
    "Gen Z–Gossip": "Curated for a generation that embodies expressive judgment — from spilling tea to holding receipts, where chatter and commentary are cultural fuel.",
    "Gen Z–Alt Hustle": "Curated for a generation that turns ambition into side hustles — from reselling sneakers to trading crypto, stacking multiple income streams as lifestyle.",
    "Gen Z–Cause Identity": "Curated for a generation that wears values as selfhood — from climate to equity, politics to self-realization, where causes are more than beliefs, they are identity.",
    "Gen Z–Prompted": "Curated for a generation shaped by algorithms and AI — where prompts, tools, and digital systems influence creativity, decisions, and identity itself.",
    # MILLENNIAL (8)
    "Millennial–Aware": "Curated for a generation that made self and public awareness mainstream — from therapy talk to empathy, inclusivity, and accountability.",
    "Millennial–Foodstagram": "Curated for a generation that turned food into cultural identity — from brunch rituals to food trucks to Michelin stars.",
    "Millennial–Growth-Minded": "Curated for a generation that made self-improvement a cultural identity — where life became a project of perpetual growth.",
    "Millennial–Spin Juice": "Curated for a generation that made boutique fitness and clean living their social stage — where wellness replaced nightlife.",
    "Millennial–Startup Nation": "Curated for a generation that turned the startup boom into identity — where disruption and hustle became cultural posture.",
    "Millennial–Throwback": "Curated for a generation that made nostalgia a cultural identity — where rewatch culture, retro fashion, and collective memory rule.",
    "Millennial–Wanderlust": "Curated for a generation that made travel into identity — where movement, discovery, and romanticized journeys define lifestyle.",
    "Millennial–Vibing": "Curated for a generation that turned lifestyle into aesthetic — from curated feeds to festival culture, where vibes became identity.",
    # GEN X (8)
    "Gen X–\"Brand\" New World": "Curated for a generation that grew up in a branded world — where logos, ads, and consumerism formed cultural identity.",
    "Gen X–Crossfaded": "Curated for a generation raised analog and fluent digital — bridging typewriters to smartphones with pragmatic adaptability.",
    "Gen X–Free World": "Curated for a generation defined by freedom from conflict — where leisure, food, expression, and individuality became daily life.",
    "Gen X–Isn't It Ironic?": "Curated for a generation that made sarcasm, irony, and skeptical cool a defining cultural language.",
    "Gen X–Latchkey Life": "Curated for a generation that raised itself — where independence and individuality became default posture.",
    "Gen X–Mixtape Society": "Curated for a generation that lived the first true cultural blend — fast food, travel, music, and shared habits forming universal relatability.",
    "Gen X–Pop Language": "Curated for a generation united by shared entertainment dialect — movies, music, sports icons as global shorthand.",
    "Gen X–Teen Spirit": "Curated for a generation that mainstreamed youth culture — music, rebellion, and fashion shaping the cultural center.",
    # BOOMER (8)
    "Boomer–Ambition Age": "Curated for a generation that turned career into identity — where upward mobility became cultural norm.",
    "Boomer–Camelot": "Curated for a generation shaped by early optimism — civic purpose, progress, and structured pathways.",
    "Boomer–Counterculture": "Curated for a generation that broke from mainstream order — psychedelia, free love, rebellion as cultural identity.",
    "Boomer–The Living Room": "Curated for a generation that made domestic stability a cultural center — home, family, and tradition anchoring daily life.",
    "Boomer–Marching Forward": "Curated for a generation that bridged tradition and progress — steady advancement, resilience, and civic participation.",
    "Boomer–Shifting Roles": "Curated for a generation adapting to new social, family, and work identities later in life.",
    "Boomer–Suburbia": "Curated for a generation defined by suburban expansion — neighborhoods, routine, order, community.",
    "Boomer–Universal Soundtrack": "Curated for a generation united by shared music and culture — the soundtrack of collective living.",
}

# Grouped by cohort for selection logic
GENERATIONS_BY_COHORT: Dict[str, List[str]] = {
    "Gen Z": [
        "Gen Z–Cloud Life", "Gen Z–Fast Culture", "Gen Z–Main Character Energy", "Gen Z–SelfTok",
        "Gen Z–Gossip", "Gen Z–Alt Hustle", "Gen Z–Cause Identity", "Gen Z–Prompted",
    ],
    "Millennial": [
        "Millennial–Aware", "Millennial–Foodstagram", "Millennial–Growth-Minded", "Millennial–Spin Juice",
        "Millennial–Startup Nation", "Millennial–Throwback", "Millennial–Wanderlust", "Millennial–Vibing",
    ],
    "Gen X": [
        "Gen X–\"Brand\" New World", "Gen X–Crossfaded", "Gen X–Free World", "Gen X–Isn't It Ironic?",
        "Gen X–Latchkey Life", "Gen X–Mixtape Society", "Gen X–Pop Language", "Gen X–Teen Spirit",
    ],
    "Boomer": [
        "Boomer–Ambition Age", "Boomer–Camelot", "Boomer–Counterculture", "Boomer–The Living Room",
        "Boomer–Marching Forward", "Boomer–Shifting Roles", "Boomer–Suburbia", "Boomer–Universal Soundtrack",
    ],
}

ALL_GENERATIONAL_NAMES: Set[str] = set(GENERATIONS.keys())

# Build normalized generational name map for fuzzy matching
_NORMALIZED_GENERATIONAL_MAP: Dict[str, str] = {}
for _gen_name in ALL_GENERATIONAL_NAMES:
    # Normalize: "Gen Z–Prompted" -> "gen z prompted", "Gen-Z Prompted" -> "gen z prompted"
    _normalized = _gen_name.lower().replace("–", " ").replace("-", " ").replace("—", " ")
    _normalized = " ".join(_normalized.split())  # collapse whitespace
    _NORMALIZED_GENERATIONAL_MAP[_normalized] = _gen_name


def normalize_generational_name(name: str) -> Optional[str]:
    """Normalize a generational segment name to its canonical form.
    
    Handles variations like:
    - "Gen-Z Prompted" -> "Gen Z–Prompted"
    - "Gen Z - Prompted" -> "Gen Z–Prompted"
    - "Millennial-Growth-Minded" -> "Millennial–Growth-Minded"
    """
    if not name:
        return None
    # Direct match
    if name in ALL_GENERATIONAL_NAMES:
        return name
    # Normalize and lookup
    normalized = name.lower().replace("–", " ").replace("-", " ").replace("—", " ")
    normalized = " ".join(normalized.split())
    return _NORMALIZED_GENERATIONAL_MAP.get(normalized)


# ────────────────────────────────────────────────────────────────────────────
# B. MULTICULTURAL EXPRESSIONS (30 total)
# Cultural identity overlays applied for multicultural initiatives.
# Only included when the campaign brief calls for it.
# ────────────────────────────────────────────────────────────────────────────

MULTICULTURAL_EXPRESSIONS: Dict[str, Dict[str, str]] = {
    # Black American Culture (5)
    "Everyday Joy": "Curated for those who find strength in laughter, food, and family — where backyard cookouts, block parties, and shared stories turn ordinary time into celebration, joy as both ritual and resilience.",
    "Faith & Fellowship": "Curated for those who find purpose in spirit, service, and song — where worship, devotion, and community turn belief into rhythm and replenishment.",
    "Cultural Tastemakers": "Curated for those who lead with style, rhythm, and voice — where music, fashion, and art become community currency and global influence.",
    "HBCU Pride": "Curated for those who see education, culture, and excellence as a shared calling — where legacy becomes movement and knowledge becomes communal pride.",
    "Afrofuturism & Innovation": "Curated for those who see technology, imagination, and artistry as liberation — where creativity becomes a tool for designing tomorrow.",
    # Latino / Hispanic Culture (5)
    "First-Gen Hustle": "Curated for those who turn resilience into progress — where bilingual identity, ambition, and family pride fuel upward mobility and cultural momentum.",
    "Familia Forward": "Curated for those who define success through care, connection, and community — where multigenerational unity shapes identity, decisions, and joy.",
    "Ritmo & Roots": "Curated for those who live where rhythm, flavor, and family blend — where music, dance, and food turn memory into motion and heritage into expression.",
    "Barrio Creators": "Curated for those who turn community into creativity — where neighborhood pride fuels art, fashion, hustle, and cultural entrepreneurship.",
    "Faith · Fútbol · Flavor": "Curated for those whose devotion extends from church to stadium to kitchen — where faith, sport, and celebration form one shared rhythm of identity.",
    # AAPI Culture (5)
    "K-Wave": "Curated for those who broadcast style and sound as cultural currency — where music, beauty, fashion, and fandom set pace for global culture.",
    "Diaspora Foodies": "Curated for those who carry heritage through taste — where flavor, nostalgia, and reinvention are expressed through kitchens, street food, and global palettes.",
    "Generational Bridge": "Curated for those balancing duty and self-definition — where respect for elders meets modern identity, and bilingual life becomes cultural translation.",
    "STEM & Startups": "Curated for those who build the future through focus and discipline — where STEM achievement and entrepreneurship become family legacy and cultural proof.",
    "Heritage Creators": "Curated for those who reshape tradition through design and storytelling — where art, aesthetics, and craft keep roots alive in modern form.",
    # South Asian / Desi Culture (5)
    "Bollywood to B-School": "Curated for those who mix spotlight with scholarship — where cinema, charisma, and study share the same rhythm of mastery and ambition.",
    "Faith & Family (Desi)": "Curated for those who treat devotion and duty as daily rhythm — where prayer, service, and household stability shape identity and purpose.",
    "Desi Creators": "Curated for those who remix heritage through digital storytelling — where identity becomes art across reels, runways, and community platforms.",
    "Second-Gen Synth": "Curated for those who translate dual identity into advantage — where bicultural fluency, ambition, and balance form hybrid strength.",
    "Spice Route Entrepreneurs": "Curated for those who inherit trade as instinct — where commerce, tradition, and modern scale turn heritage into enterprise.",
    # MENA Culture (5)
    "Heritage & Hospitality": "Curated for those who treat welcoming as identity — where generosity, tradition, and community shape cultural rhythm.",
    "Faith & Modernity": "Curated for those blending devotion with contemporary life — where ritual and innovation exist in seamless harmony.",
    "Diaspora Innovators": "Curated for those who elevate tradition through design and entrepreneurship — where modern identity and heritage drive reinvention.",
    "Art & Architecture": "Curated for those who express culture through craft — where geometric beauty, storytelling, and design honor legacy.",
    "Next-Gen Creators": "Curated for those shaping the region's modern renaissance — where youth, creativity, and technology meet heritage and future vision.",
    # Hybrid / Global Culture (5)
    "Culture Collide": "Curated for those who mix identities with ease — where global influences merge into new forms of expression and belonging.",
    "Fusion Foodies": "Curated for those who tell stories through flavor — where multicultural kitchens turn heritage into experiment and community.",
    "Hybrid Households": "Curated for those blending cultures within the home — where rituals, languages, and traditions coexist and evolve.",
    "Global Millennial": "Curated for those defined by travel, digital culture, and global connection — where identity is shaped by movement and exposure.",
    "New Americana": "Curated for those who define modern U.S. identity — where blended heritage, global influences, and new traditions form a cultural future.",
}

MULTICULTURAL_BY_LINEAGE: Dict[str, List[str]] = {
    "Black American": ["Everyday Joy", "Faith & Fellowship", "Cultural Tastemakers", "HBCU Pride", "Afrofuturism & Innovation"],
    "Latino / Hispanic": ["First-Gen Hustle", "Familia Forward", "Ritmo & Roots", "Barrio Creators", "Faith · Fútbol · Flavor"],
    "AAPI": ["K-Wave", "Diaspora Foodies", "Generational Bridge", "STEM & Startups", "Heritage Creators"],
    "South Asian / Desi": ["Bollywood to B-School", "Faith & Family (Desi)", "Desi Creators", "Second-Gen Synth", "Spice Route Entrepreneurs"],
    "MENA": ["Heritage & Hospitality", "Faith & Modernity", "Diaspora Innovators", "Art & Architecture", "Next-Gen Creators"],
    "Hybrid / Global": ["Culture Collide", "Fusion Foodies", "Hybrid Households", "Global Millennial", "New Americana"],
}


# ────────────────────────────────────────────────────────────────────────────
# C. LOCAL CULTURE SEGMENTS (125 DMAs)
# Geographic identity overlays applied when the campaign activates in specific markets.
# Only used when: Geography = DMA, Locality is core to the buy, campaign needs regional nuance.
# Do NOT apply to national campaigns.
# ────────────────────────────────────────────────────────────────────────────

# List of DMA Segments (125) - exact from RJM INGREDIENT CANON 11.26.25
LOCAL_CULTURE_DMAS: List[str] = [
    "Albany-NY Culture", "Albuquerque-Santa Fe Culture", "Alaska Culture", "Ann Arbor Culture",
    "Atlanta Culture", "Austin Culture", "Baton Rouge Culture", "Birmingham Culture", "Boise Culture",
    "Boston Culture", "Bozeman Culture", "Bucks County Culture", "Buffalo Culture", "Cape Cod Culture",
    "Capital Culture", "Charleston Culture", "Charlotte Culture", "Chicago (National) Culture",
    "Cincinnati Culture", "Cleveland Culture", "College Station Culture", "Colorado Springs Culture",
    "Columbus Culture", "Corpus Christi Culture", "Dallas Culture", "Delaware Culture", "Denver/Boulder Culture",
    "Des Moines Culture", "Detroit Culture", "El Paso Culture", "Eugene Culture", "Fairfield County Culture",
    "Fayetteville-Bentonville Culture", "Fresno Culture", "Grand Rapids/Kalamazoo Culture",
    "Green Bay/Appleton Culture", "Hampton Roads Culture", "Hartford Culture", "Heartland Plains Culture",
    "Hawaii Culture", "Houston Culture", "Hudson Valley Culture", "Huntsville Culture",
    "Indianapolis Culture", "Jackson Culture", "Jacksonville Culture", "Jersey Shore Culture",
    "Kansas City Culture", "Knoxville Culture", "Lafayette Culture", "Las Vegas Culture", "Lexington Culture",
    "Lincoln Culture", "Little Rock Culture", "Long Island Culture", "Los Angeles Culture", "Louisville Culture",
    "Madison Culture", "Maine Culture", "Memphis Culture", "Miami Culture", "Milwaukee Culture",
    "Minneapolis/St. Paul Culture", "Mobile Culture", "Montgomery-GA Culture", "Nashville Culture",
    "Napa Valley Culture", "New Hampshire Culture", "New Haven Culture", "New Orleans Culture",
    "New York City Culture", "North Dakota Culture", "North Jersey Culture", "Northwest Indiana Culture",
    "Oakland Culture", "Omaha Culture", "Orange County Culture", "Palm Springs Culture",
    "Philadelphia Culture", "Phoenix/Scottsdale Culture", "Pittsburgh Culture", "Portland Culture",
    "Providence Culture", "Raleigh-Durham Culture", "Reno-Tahoe Culture", "Richmond Culture",
    "Rochester Culture", "Sacramento Culture", "Salt Lake City Culture", "San Antonio Culture",
    "San Diego Culture", "San Francisco Culture", "San Jose Culture", "Savannah Culture", "Seattle Culture",
    "Sioux Falls Culture", "South Jersey Culture", "Spokane Culture", "Springfield Culture",
    "St. Louis Culture", "Tallahassee-Gulf/Panhandle Culture", "Tampa Bay Culture", "Topeka Culture",
    "Tulsa Culture", "Upper Peninsula Culture", "Vail-Aspen Culture", "Vermont Culture", "Waco Culture",
    "Washington-DC Culture", "West Palm Culture", "West Texas Culture", "West Virginia Culture",
    "Westchester County Culture", "Wichita Culture", "Wyoming Culture",
]

# Quick lookup set for validation
LOCAL_CULTURE_SET: Set[str] = set(LOCAL_CULTURE_DMAS)


# ════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

# Keyword heuristics for category inference
CATEGORY_KEYWORDS: Dict[str, Sequence[str]] = {
    "QSR": ["qsr", "fast food", "drive-thru", "quick service", "burger", "fries", "pizza chain"],
    "Culinary & Dining": ["culinary", "dining", "chef", "kitchen", "recipe", "restaurant", "brunch", "menu", "cafe"],
    "Retail & E-Commerce": ["retail", "apparel", "fashion", "shopping", "store", "threads", "e-commerce", "boutique"],
    "Auto": ["auto", "automotive", "suv", "car", "truck", "motors", "dealership", "vehicle"],
    "Finance & Insurance": ["bank", "finance", "insurance", "credit", "loan", "mortgage", "wealth", "investment"],
    "Health & Pharma": ["health", "wellness", "pharma", "fitness", "care", "medical", "vitamin"],
    "Tech & Wireless": ["tech", "wireless", "mobile", "software", "hardware", "device", "app", "digital"],
    "Travel & Hospitality": ["travel", "hotel", "hospitality", "vacation", "tourism", "resort", "airline"],
    "Sports & Fitness": ["sports", "fitness", "athletic", "athlete", "gym", "workout"],
    "CPG": ["cpg", "consumer packaged", "grocery", "household", "cleaning", "personal care"],
    "Home & DIY": ["home", "diy", "renovation", "furniture", "garden", "improvement"],
    "Luxury & Fashion": ["luxury", "couture", "runway", "glam", "designer", "high-end", "premium fashion", "beauty", "cosmetics", "skincare", "makeup", "l'oréal", "loreal"],
    "Alcohol & Spirits": ["spirits", "alcohol", "brew", "distillery", "cocktail", "beer", "wine", "whiskey"],
    "Entertainment": ["entertainment", "streaming", "media", "music", "film", "movie", "tv", "show"],
}

# Brands that span multiple categories (dual anchors)
DUAL_ANCHOR_BRANDS: Dict[str, List[str]] = {
    "l'oréal": ["CPG", "Luxury & Fashion"],
    "loreal": ["CPG", "Luxury & Fashion"],
    "l'oreal": ["CPG", "Luxury & Fashion"],
    "estee lauder": ["CPG", "Luxury & Fashion"],
    "estée lauder": ["CPG", "Luxury & Fashion"],
    "nike": ["Sports & Fitness", "Retail & E-Commerce"],
    "adidas": ["Sports & Fitness", "Retail & E-Commerce"],
    "apple": ["Tech & Wireless", "Luxury & Fashion"],
    "samsung": ["Tech & Wireless", "Retail & E-Commerce"],
    "amazon": ["Retail & E-Commerce", "Tech & Wireless"],
    "uber": ["Tech & Wireless", "Travel & Hospitality"],
    "lyft": ["Tech & Wireless", "Travel & Hospitality"],
    "airbnb": ["Travel & Hospitality", "Tech & Wireless"],
    "disney": ["Entertainment", "Travel & Hospitality"],
    "marriott": ["Travel & Hospitality", "Luxury & Fashion"],
    "hilton": ["Travel & Hospitality", "Luxury & Fashion"],
}


def infer_category(text: str) -> str:
    """Infer primary advertising category using keyword heuristics."""
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "CPG"  # Default fallback


def get_brand_categories(brand_name: str) -> List[str]:
    """Return list of categories for a brand (handles dual-anchor brands)."""
    lowered = brand_name.lower().strip()
    if lowered in DUAL_ANCHOR_BRANDS:
        return DUAL_ANCHOR_BRANDS[lowered]
    return []


def get_category_personas(category: str) -> List[str]:
    """Return persona names for a given advertising category."""
    return CATEGORY_PERSONA_MAP.get(category, [])


def get_category_anchors(category: str) -> List[str]:
    """Return anchor segments for a given category."""
    return AD_CATEGORY_ANCHORS.get(category, ["RJM Persona Anchor"])


def get_dual_anchors(brand_name: str, primary_category: str) -> List[str]:
    """
    Return anchors for a brand, handling dual-anchor cases.
    For brands like L'Oréal, returns both RJM CPG and RJM Luxury & Fashion.
    """
    brand_categories = get_brand_categories(brand_name)
    if brand_categories:
        # Use the brand's defined dual categories
        anchors = []
        for cat in brand_categories:
            cat_anchors = AD_CATEGORY_ANCHORS.get(cat, [])
            for anchor in cat_anchors:
                if anchor not in anchors:
                    anchors.append(anchor)
        return anchors[:2]  # Max 2 anchors
    # Fall back to primary category anchor
    return get_category_anchors(primary_category)[:2]


def get_persona_phylum(persona_name: str) -> Optional[str]:
    """Return the phylum for a given persona name."""
    return PERSONA_TO_PHYLUM.get(persona_name)


def _normalize_persona_name(name: str) -> str:
    """Normalize persona name for matching (handle hyphen/space/quote variations)."""
    # Replace various dashes and special chars with spaces
    result = name.replace("-", " ").replace("–", " ").replace("—", " ")
    # Remove quotes and apostrophes for matching
    result = result.replace("'", "").replace("'", "").replace('"', "")
    # Normalize whitespace
    result = " ".join(result.split())
    return result.strip()


# Build comprehensive set of ALL canon persona names from both category and phylum maps
_ALL_CANON_PERSONAS: Set[str] = set()
_NORMALIZED_CANON_MAP: Dict[str, str] = {}  # normalized_lower -> original

# Add from phylum map
for _name in PERSONA_TO_PHYLUM.keys():
    _ALL_CANON_PERSONAS.add(_name)
    _normalized = _normalize_persona_name(_name).lower()
    if _normalized not in _NORMALIZED_CANON_MAP:
        _NORMALIZED_CANON_MAP[_normalized] = _name

# Add from category map (may have different naming conventions)
for _category_personas in CATEGORY_PERSONA_MAP.values():
    for _name in _category_personas:
        _ALL_CANON_PERSONAS.add(_name)
        _normalized = _normalize_persona_name(_name).lower()
        if _normalized not in _NORMALIZED_CANON_MAP:
            _NORMALIZED_CANON_MAP[_normalized] = _name


def is_canon_persona(name: str) -> bool:
    """Check if a persona name is in the canon (handles name variations)."""
    if not name:
        return False
    # Direct match
    if name in _ALL_CANON_PERSONAS:
        return True
    # Try normalized matching
    normalized = _normalize_persona_name(name).lower()
    return normalized in _NORMALIZED_CANON_MAP


def get_canonical_name(name: str) -> str:
    """Get the canonical version of a persona name."""
    if not name:
        return name
    # Direct match - return as-is
    if name in _ALL_CANON_PERSONAS:
        return name
    # Try normalized matching
    normalized = _normalize_persona_name(name).lower()
    return _NORMALIZED_CANON_MAP.get(normalized, name)


def get_generational_segment(cohort: str, index: int = 0) -> Optional[str]:
    """Get a generational segment by cohort and index (for rotation)."""
    cohort_segments = GENERATIONS_BY_COHORT.get(cohort, [])
    if not cohort_segments:
        return None
    return cohort_segments[index % len(cohort_segments)]


def get_generational_description(segment_name: str) -> Optional[str]:
    """Get the description for a generational segment."""
    return GENERATIONS.get(segment_name)


def get_multicultural_expressions(lineage: str) -> List[str]:
    """Get multicultural expression names for a given cultural lineage."""
    return MULTICULTURAL_BY_LINEAGE.get(lineage, [])


def get_multicultural_description(expression_name: str) -> Optional[str]:
    """Get the description for a multicultural expression."""
    return MULTICULTURAL_EXPRESSIONS.get(expression_name)


# ════════════════════════════════════════════════════════════════════════════
# LOCAL BRIEF DETECTION
# ════════════════════════════════════════════════════════════════════════════

US_STATES = [
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
    "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
    "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada", "new hampshire",
    "new jersey", "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington", "west virginia",
    "wisconsin", "wyoming",
]

LOCAL_KEYWORDS = [
    "dma", "market-level", "market level", "statewide",
    "by state", "by city", "local market", "local markets", "specific markets",
    "geo-target", "geo target", "geotarget", "dma-targeted", "dma targeted",
]

# Major city names for detection
MAJOR_CITIES = [
    "new york", "los angeles", "chicago", "houston", "phoenix", "philadelphia", "san antonio",
    "san diego", "dallas", "austin", "san jose", "san francisco", "seattle", "denver",
    "boston", "nashville", "atlanta", "miami", "detroit", "minneapolis", "charlotte",
    "portland", "las vegas", "baltimore", "milwaukee", "albuquerque", "tucson", "fresno",
    "sacramento", "kansas city", "cleveland", "pittsburgh", "orlando", "tampa",
]


def is_local_brief(text: str) -> bool:
    """Detect whether a brief references DMA/state/regional targeting."""
    lowered = text.lower()
    
    # Check explicit local keywords
    if any(keyword in lowered for keyword in LOCAL_KEYWORDS):
        return True
    
    # Check state names
    if any(state in lowered for state in US_STATES):
        return True
    
    # Check major city names
    if any(city in lowered for city in MAJOR_CITIES):
        return True
    
    return False


def get_local_culture_segment(dma_hint: str) -> Optional[str]:
    """Try to match a DMA hint to a Local Culture segment."""
    lowered = dma_hint.lower()
    for segment in LOCAL_CULTURE_DMAS:
        # Extract the city/region name from the segment
        base_name = segment.replace(" Culture", "").lower()
        if base_name in lowered or lowered in base_name:
            return segment
    return None


# ════════════════════════════════════════════════════════════════════════════
# MULTICULTURAL BRIEF DETECTION
# ════════════════════════════════════════════════════════════════════════════

MULTICULTURAL_KEYWORDS: Dict[str, List[str]] = {
    "Black American": ["black", "african american", "african-american", "hbcu", "black culture", "black community"],
    "Latino / Hispanic": ["latino", "latina", "hispanic", "spanish", "latinx", "mexican", "puerto rican", "cuban"],
    "AAPI": ["aapi", "asian", "asian american", "pacific islander", "korean", "japanese", "chinese", "vietnamese", "filipino", "k-pop", "k-wave"],
    "South Asian / Desi": ["south asian", "desi", "indian", "pakistani", "bangladeshi", "bollywood"],
    "MENA": ["mena", "middle eastern", "arab", "north african", "persian"],
    "Hybrid / Global": ["multicultural", "global", "diverse", "fusion", "hybrid"],
}


def detect_multicultural_lineage(text: str) -> Optional[str]:
    """Detect if a brief targets a specific cultural lineage."""
    lowered = text.lower()
    for lineage, keywords in MULTICULTURAL_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return lineage
    return None


# ════════════════════════════════════════════════════════════════════════════
# ROTATION LOGIC (In-Memory)
# Simple in-memory rotation tracker (non-persistent across restarts)
# ════════════════════════════════════════════════════════════════════════════

_RECENT_PERSONAS: deque[str] = deque(maxlen=120)
_RECENT_GENERATIONAL: deque[str] = deque(maxlen=40)


def register_personas_for_rotation(names: Sequence[str]) -> None:
    """Record personas that were just used to help rotation logic."""
    for name in names:
        if name not in _RECENT_PERSONAS:
            _RECENT_PERSONAS.append(name)


def register_generational_for_rotation(names: Sequence[str]) -> None:
    """Record generational segments that were just used."""
    for name in names:
        if name not in _RECENT_GENERATIONAL:
            _RECENT_GENERATIONAL.append(name)


def is_persona_recent(name: str) -> bool:
    """Check if a persona was recently used."""
    return name in _RECENT_PERSONAS


def is_generational_recent(name: str) -> bool:
    """Check if a generational segment was recently used."""
    return name in _RECENT_GENERATIONAL


def clear_rotation_cache() -> None:
    """Clear rotation caches (useful for testing)."""
    _RECENT_PERSONAS.clear()
    _RECENT_GENERATIONAL.clear()


# ════════════════════════════════════════════════════════════════════════════
# PHYLUM DIVERSITY HELPERS
# ════════════════════════════════════════════════════════════════════════════

def check_phylum_diversity(personas: List[str], min_phyla: int = 3, max_dominance: float = 0.30) -> Tuple[bool, Dict[str, int]]:
    """
    Check if a persona list meets phylum diversity requirements.
    Returns (is_valid, phylum_counts).
    """
    phylum_counts: Dict[str, int] = {}
    for name in personas:
        phylum = PERSONA_TO_PHYLUM.get(name)
        if phylum:
            phylum_counts[phylum] = phylum_counts.get(phylum, 0) + 1
    
    unique_phyla = len(phylum_counts)
    total = sum(phylum_counts.values())
    
    if total == 0:
        return False, phylum_counts
    
    max_count = max(phylum_counts.values()) if phylum_counts else 0
    dominance = max_count / total if total > 0 else 0
    
    is_valid = unique_phyla >= min_phyla and dominance <= max_dominance
    return is_valid, phylum_counts


def diversify_by_phylum(
    current: List[str],
    pool: List[str],
    target_count: int,
    min_phyla: int = 3,
    max_dominance: float = 0.30,
) -> List[str]:
    """
    Add personas from pool to current list while maintaining phylum diversity.
    """
    result = list(current)
    seen = set(result)
    
    # Track phylum counts
    phylum_counts: Dict[str, int] = {}
    for name in result:
        phylum = PERSONA_TO_PHYLUM.get(name)
        if phylum:
            phylum_counts[phylum] = phylum_counts.get(phylum, 0) + 1
    
    for name in pool:
        if len(result) >= target_count:
            break
        if name in seen:
            continue
        
        phylum = PERSONA_TO_PHYLUM.get(name)
        if not phylum:
            continue
        
        # Check if adding this persona would violate dominance
        current_count = phylum_counts.get(phylum, 0)
        new_total = len(result) + 1
        new_dominance = (current_count + 1) / new_total
        
        if new_dominance > max_dominance and len(phylum_counts) >= min_phyla:
            # Skip this persona if it would cause over-dominance
            continue
        
        result.append(name)
        seen.add(name)
        phylum_counts[phylum] = current_count + 1
    
    return result


# Log initialization
app_logger.info(
    f"RJM Ingredient Canon 11.26.25 loaded: "
    f"{len(CATEGORY_PERSONA_MAP)} categories, "
    f"{len(PHYLUM_PERSONA_MAP)} phyla, "
    f"{len(GENERATIONS)} generations, "
    f"{len(MULTICULTURAL_EXPRESSIONS)} multicultural expressions, "
    f"{len(LOCAL_CULTURE_DMAS)} DMA segments"
)

