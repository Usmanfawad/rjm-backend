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

PHASE 1 FIXES (per Jesse's feedback):
1. Default persona gravity - rotation pressure / anti-repeat logic
2. Persona Highlights vs Insights - HARD SEPARATION enforced
3. Sunset personas - strict allowlist, no deprecated personas
4. Ad-category anchor segments - reinstated in portfolio
5. Category edge cases - override logic for multi-category brands
"""

from __future__ import annotations

import random
from collections import deque
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.config.logger import app_logger


# ════════════════════════════════════════════════════════════════════════════
# SUNSET / DEPRECATED PERSONAS (STRICT ALLOWLIST ENFORCEMENT)
# These personas are NO LONGER part of the active ingredient canon.
# They MUST NOT appear in any generated programs.
# ════════════════════════════════════════════════════════════════════════════

DEPRECATED_PERSONAS: Set[str] = {
    # Legacy personas retired from canon
    "Culture Maven",  # Replaced by Culture Connoisseur
    "Money Mover",    # Consolidated into Power Broker
    "Cash Flow",      # Consolidated into Power Broker
    "Wellness Warrior",  # Replaced by Biohacker / Gym Obsessed
    "Health Nut",     # Replaced by Clean Eats
    "Fitness Fanatic",  # Replaced by Gym Obsessed
    "Tech Savant",    # Replaced by Techie / Innovator
    "Digital Native", # Too generic, use specific personas
    "Eco Warrior",    # Replaced by Green Pioneer
    "Social Climber", # Retired
    "Trend Spotter",  # Consolidated into Hype Seeker
    "Brand Loyalist", # Retired - too generic
    "Impulse Spender",  # Consolidated into Impulse Buyer
    "Deal Seeker",    # Consolidated into Bargain Hunter
    "Coupon Clipper", # Consolidated into Savvy Shopper
    "Soccer Mom",     # Retired - use Sports Parent
    "Busy Mom",       # Retired - use Single Parent / Caregiver
    "Working Mom",    # Retired - use Single Parent
    "Daddy Daycare",  # Retired - use Single Parent
    "Adventure Seeker",  # Consolidated into Adrenaline Junkie
    "Thrill Seeker",  # Consolidated into Adrenaline Junkie
    "Party Animal",   # Retired
    "Night Crawler",  # Consolidated into Night Owl
    "Fashion Forward",  # Consolidated into Fast Fashionista
    "Style Maven",    # Consolidated into Stylista
    "Wine Snob",      # Consolidated into Sideways
    "Beer Connoisseur",  # Consolidated into Beer League
    "Coffee Addict",  # Consolidated into Caffeine Fiend
    "Foodie",         # Too generic - use Chef / Bourdain Mode / Michelin Chaser
    "Music Lover",    # Too generic - use specific music phyla
    "Sports Fan",     # Too generic - use specific sports personas
    "Car Enthusiast", # Consolidated into Revved / Fast Lane
    "Pet Parent",     # Consolidated into Dog Parent / Cat Person / Pawrent
    "Animal Lover",   # Consolidated into Rescuer
}


# ════════════════════════════════════════════════════════════════════════════
# CATEGORY EDGE CASES — Override Logic for Multi-Category Brands
# Explicit mappings for brands that span categories (Phase 1 Fix #5)
# ════════════════════════════════════════════════════════════════════════════

BRAND_CATEGORY_OVERRIDES: Dict[str, str] = {
    # Grocery/Supermarket - primary category by business model
    "whole foods": "Retail & E-Commerce",
    "whole foods market": "Retail & E-Commerce",
    "trader joe's": "Retail & E-Commerce",
    "trader joes": "Retail & E-Commerce",
    "kroger": "Retail & E-Commerce",
    "safeway": "Retail & E-Commerce",
    "publix": "Retail & E-Commerce",
    "wegmans": "Retail & E-Commerce",
    "aldi": "Retail & E-Commerce",
    "costco": "Retail & E-Commerce",
    "sam's club": "Retail & E-Commerce",
    
    # QSR-primary (even if they have dining elements)
    "dunkin": "QSR",
    "dunkin'": "QSR",
    "dunkin donuts": "QSR",
    "mcdonald's": "QSR",
    "mcdonalds": "QSR",
    "burger king": "QSR",
    "wendy's": "QSR",
    "wendys": "QSR",
    "taco bell": "QSR",
    "chick-fil-a": "QSR",
    "chick fil a": "QSR",
    "chipotle": "QSR",
    "five guys": "QSR",
    "in-n-out": "QSR",
    "in n out": "QSR",
    "shake shack": "QSR",
    "panda express": "QSR",
    "popeyes": "QSR",
    "kfc": "QSR",
    "subway": "QSR",
    "domino's": "QSR",
    "dominos": "QSR",
    "pizza hut": "QSR",
    "papa john's": "QSR",
    "papa johns": "QSR",
    "sonic": "QSR",
    "jack in the box": "QSR",
    "carl's jr": "QSR",
    "hardee's": "QSR",
    "arby's": "QSR",
    "arbys": "QSR",
    "white castle": "QSR",
    "whataburger": "QSR",
    "wingstop": "QSR",
    "buffalo wild wings": "QSR",
    "jersey mike's": "QSR",
    "jimmy john's": "QSR",
    "firehouse subs": "QSR",
    
    # Culinary & Dining (sit-down experience is primary)
    "starbucks": "Culinary & Dining",
    "olive garden": "Culinary & Dining",
    "applebee's": "Culinary & Dining",
    "applebees": "Culinary & Dining",
    "chili's": "Culinary & Dining",
    "chilis": "Culinary & Dining",
    "outback steakhouse": "Culinary & Dining",
    "outback": "Culinary & Dining",
    "red lobster": "Culinary & Dining",
    "texas roadhouse": "Culinary & Dining",
    "longhorn steakhouse": "Culinary & Dining",
    "cracker barrel": "Culinary & Dining",
    "cheesecake factory": "Culinary & Dining",
    "p.f. chang's": "Culinary & Dining",
    "pf changs": "Culinary & Dining",
    "ihop": "Culinary & Dining",
    "denny's": "Culinary & Dining",
    "dennys": "Culinary & Dining",
    "waffle house": "Culinary & Dining",
    "panera bread": "Culinary & Dining",
    "panera": "Culinary & Dining",
    "noodles & company": "Culinary & Dining",
    "sweetgreen": "Culinary & Dining",
    "cava": "Culinary & Dining",
    "hillstone": "Culinary & Dining",
    "first watch": "Culinary & Dining",
    
    # Coffee shops (Culinary experience)
    "peet's coffee": "Culinary & Dining",
    "peets": "Culinary & Dining",
    "blue bottle": "Culinary & Dining",
    "blue bottle coffee": "Culinary & Dining",
    "philz coffee": "Culinary & Dining",
    "intelligentsia": "Culinary & Dining",
    "la colombe": "Culinary & Dining",
    "counter culture": "Culinary & Dining",
    
    # Delivery/platform food
    "uber eats": "QSR",
    "ubereats": "QSR",
    
    # Luxury brands (ensure proper categorization)
    "fendi": "Luxury & Fashion",
    "gucci": "Luxury & Fashion",
    "louis vuitton": "Luxury & Fashion",
    "lv": "Luxury & Fashion",
    "chanel": "Luxury & Fashion",
    "prada": "Luxury & Fashion",
    "dior": "Luxury & Fashion",
    "hermes": "Luxury & Fashion",
    "hermès": "Luxury & Fashion",
    "burberry": "Luxury & Fashion",
    "versace": "Luxury & Fashion",
    "balenciaga": "Luxury & Fashion",
    "bottega veneta": "Luxury & Fashion",
    "saint laurent": "Luxury & Fashion",
    "ysl": "Luxury & Fashion",
    "valentino": "Luxury & Fashion",
    "armani": "Luxury & Fashion",
    "givenchy": "Luxury & Fashion",
    "celine": "Luxury & Fashion",
    "loewe": "Luxury & Fashion",
    "miu miu": "Luxury & Fashion",
    "tiffany": "Luxury & Fashion",
    "tiffany & co": "Luxury & Fashion",
    "cartier": "Luxury & Fashion",
    "rolex": "Luxury & Fashion",
    "omega": "Luxury & Fashion",
    "patek philippe": "Luxury & Fashion",
    "sephora": "Luxury & Fashion",
    "ulta": "Luxury & Fashion",
    "nordstrom": "Luxury & Fashion",
    "neiman marcus": "Luxury & Fashion",
    "saks fifth avenue": "Luxury & Fashion",
    "saks": "Luxury & Fashion",
    "bloomingdale's": "Luxury & Fashion",
    "bloomingdales": "Luxury & Fashion",
    "bergdorf goodman": "Luxury & Fashion",
    
    # Telecom/Wireless (Tech & Wireless even if they sell devices)
    "verizon": "Tech & Wireless",
    "at&t": "Tech & Wireless",
    "att": "Tech & Wireless",
    "t-mobile": "Tech & Wireless",
    "tmobile": "Tech & Wireless",
    "sprint": "Tech & Wireless",
    "xfinity": "Tech & Wireless",
    "comcast": "Tech & Wireless",
    "spectrum": "Tech & Wireless",
    "cox": "Tech & Wireless",
    
    # Fitness brands
    "peloton": "Sports & Fitness",
    "equinox": "Sports & Fitness",
    "orangetheory": "Sports & Fitness",
    "planet fitness": "Sports & Fitness",
    "la fitness": "Sports & Fitness",
    "24 hour fitness": "Sports & Fitness",
    "crossfit": "Sports & Fitness",
    "soulcycle": "Sports & Fitness",
    "barry's": "Sports & Fitness",
    "f45": "Sports & Fitness",
    
    # Athletic brands (dual Sports & Retail)
    "nike": "Sports & Fitness",
    "adidas": "Sports & Fitness",
    "under armour": "Sports & Fitness",
    "lululemon": "Sports & Fitness",
    "new balance": "Sports & Fitness",
    "puma": "Sports & Fitness",
    "reebok": "Sports & Fitness",
    "asics": "Sports & Fitness",
    "brooks": "Sports & Fitness",
    
    # Alcohol brands
    "budweiser": "Alcohol & Spirits",
    "bud light": "Alcohol & Spirits",
    "miller lite": "Alcohol & Spirits",
    "coors": "Alcohol & Spirits",
    "corona": "Alcohol & Spirits",
    "heineken": "Alcohol & Spirits",
    "stella artois": "Alcohol & Spirits",
    "guinness": "Alcohol & Spirits",
    "jack daniels": "Alcohol & Spirits",
    "jack daniel's": "Alcohol & Spirits",
    "johnnie walker": "Alcohol & Spirits",
    "jameson": "Alcohol & Spirits",
    "grey goose": "Alcohol & Spirits",
    "absolut": "Alcohol & Spirits",
    "smirnoff": "Alcohol & Spirits",
    "patron": "Alcohol & Spirits",
    "don julio": "Alcohol & Spirits",
    "casamigos": "Alcohol & Spirits",
    "white claw": "Alcohol & Spirits",
    "truly": "Alcohol & Spirits",
}

# Meaning-based overlay persona sets (used to loosen category hard-lock for edge briefs)
PET_SERVICE_PERSONAS: Set[str] = {
    # Core pet personas (PRIORITIZE THESE)
    "Dog Parent", "Cat Person", "Rescuer", "Pack Leader", "Petfluencer",
    "Pawrent", "Best in Show", "Lulu",
    # Community / local (pet owners are local customers)
    "Neighborhood Watch", "Volunteer", "Hometown Hero", "Main Street",
    # Caregiving mindset (pet ownership is caregiving)
    "Caregiver", "Single Parent", "Empty Nester",
    # Outdoor / active with pets
    "Nature Lover", "Hiker", "Trailblazer", "Morning Stroll", "Weekend Warrior",
}

EDUCATION_PERSONAS: Set[str] = {
    # Core education & growth personas (PRIORITIZE THESE)
    "Scholar", "Reader", "Writer", "Coach", "Mentor", "Planner", "Self-Love",
    "Modern Monk", "Optimist", "Journey", "Legacy",
    # Flex-life / returning learner personas (adult education audience)
    "Single Parent", "Caregiver", "Empty Nester", "Retiree",
    # Digital/remote learning
    "Digital Nomad", "Techie",
    # Career growth (use sparingly - not the primary audience)
    "Builder", "Innovator", "Entrepreneur",
}

CIVIC_PERSONAS: Set[str] = {
    # Community & local pride (PRIORITIZE THESE)
    "Neighborhood Watch", "Volunteer", "Main Street", "PTA", "Mayor",
    "Hometown Hero", "Southern Hospitality",
    # Values & tradition
    "Faith", "Believer", "Legacy", "Family Table",
    # Civic engagement
    "Potomac Power", "Social Architect", "Journey",
    # Practical voters
    "Planner", "Caregiver", "Single Parent", "Empty Nester",
}


# ════════════════════════════════════════════════════════════════════════════
# HOT PERSONAS — High-Frequency Personas Needing Rotation Pressure
# These personas are "default" selections that appear too often.
# Apply rotation pressure to ensure diversity.
# ════════════════════════════════════════════════════════════════════════════

# Per-category "hot" personas that need rotation pressure (Phase 1 Fix #1)
CATEGORY_HOT_PERSONAS: Dict[str, Set[str]] = {
    "Travel & Hospitality": {
        "Romantic Voyager", "Retreat Seeker", "Island Hopper",
    },
    "Luxury & Fashion": {
        "Closet Runway", "Fast Fashionista", "Couture Curator",
    },
    "CPG": {
        "Budget-Minded", "Savvy Shopper", "Bargain Hunter",
    },
    "QSR": {
        "Takeout Guru", "Food Truckin'", "Caffeine Fiend",
    },
    "Retail & E-Commerce": {
        "Bargain Hunter", "Budget-Minded", "Savvy Shopper", "Impulse Buyer",
    },
    "Finance & Insurance": {
        "Power Broker", "Planner", "Legacy",
    },
    "Tech & Wireless": {
        "Techie", "Digital Nomad", "Gamer",
    },
    "Entertainment": {
        "Binge Watcher", "Creator", "Gamer",
    },
    "Sports & Fitness": {
        "Gym Obsessed", "Weekend Warrior", "Sports Parent",
    },
    "Culinary & Dining": {
        "Chef", "Bourdain Mode", "Foodie",
    },
    "Health & Pharma": {
        "Self-Love", "Biohacker", "Gym Obsessed",
    },
    "Auto": {
        "Road Trip", "Weekend Warrior", "Fast Lane",
    },
    "Home & DIY": {
        "Fixer", "Modern Tradesman", "Design Maven",
    },
    "Alcohol & Spirits": {
        "Nightcapper", "Social Butterfly", "Night Owl",
    },
}


def is_hot_persona(name: str, category: str) -> bool:
    """Check if a persona is a 'hot' persona for the given category.
    
    Hot personas are frequently selected and need rotation pressure.
    """
    hot_set = CATEGORY_HOT_PERSONAS.get(category, set())
    return name in hot_set


def get_rotation_weight(name: str, category: str, recency_position: int = -1) -> float:
    """Calculate rotation weight for a persona (lower = less likely to be selected).
    
    Args:
        name: Persona name
        category: Advertising category
        recency_position: Position in recent usage queue (-1 if not recent)
    
    Returns:
        Weight between 0.1 (strongly suppress) and 1.0 (no suppression)
    """
    weight = 1.0
    
    # Hot persona penalty
    if is_hot_persona(name, category):
        weight *= 0.6  # 40% penalty for being a "hot" persona
    
    # Recency penalty (if recently used)
    if recency_position >= 0:
        if recency_position < 20:  # Very recently used
            weight *= 0.3
        elif recency_position < 50:  # Moderately recent
            weight *= 0.5
        elif recency_position < 100:  # Somewhat recent
            weight *= 0.7
    
    return max(0.1, weight)  # Never go below 0.1


# ════════════════════════════════════════════════════════════════════════════
# SECTION I — CATEGORY → PERSONA MAP
# Primary Selector — The First Layer of Every Persona Program
# ════════════════════════════════════════════════════════════════════════════

CATEGORY_PERSONA_MAP: Dict[str, List[str]] = {
    # B2B & Professional Services - for martech, data companies, SaaS, enterprise
    "B2B & Professional Services": [
        "Power Broker", "Boss", "Visionary", "Palo Alto", "Upstart", "Prime Mover", "Disruptor",
        "Maverick", "Trader", "Entrepreneur", "Builder", "Innovator", "Scholar", "Techie",
        "Digital Nomad", "Architect", "Potomac Power", "Gordon Gecko", "Planner", "Legacy",
        "LeBron", "Matador", "QB", "Coach", "Mentor", "Modern Monk", "Reader", "Writer",
        "Journey", "Morning Commute", "After Hours", "Sideways", "Trailblazer",
    ],
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
    "B2B & Professional Services": ["RJM B2B & Professional Services"],
}

# All 15 anchor names for reference (14 original + B2B)
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
    "RJM B2B & Professional Services",
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
    # B2B MUST come first - martech, data companies, enterprise, SaaS
    "B2B & Professional Services": [
        "b2b", "saas", "enterprise", "martech", "adtech", "data company", "data platform",
        "professional services", "consulting", "agency", "marketing technology",
        "stirista", "livereamp", "liveramp", "oracle data", "nielsen", "iqvia",
        "salesforce", "hubspot", "marketo", "enterprise software", "client services",
        "business intelligence", "analytics platform", "data provider", "dsp",
        "demand-side", "supply-side", "programmatic platform",
    ],
    "QSR": ["qsr", "fast food", "drive-thru", "quick service", "burger", "fries", "pizza chain"],
    "Culinary & Dining": ["culinary", "dining", "chef", "kitchen", "recipe", "restaurant", "brunch", "menu", "cafe"],
    # IMPORTANT: Order matters! More specific categories must come BEFORE broader ones.
    # "Luxury & Fashion" must come before "Retail & E-Commerce" so "luxury fashion" matches correctly.
    "Luxury & Fashion": ["luxury", "luxe", "couture", "runway", "glam", "designer", "high-end", "premium fashion", "upscale fashion", "fashion brand", "flagship store", "beauty", "cosmetics", "skincare", "makeup", "l'oréal", "loreal", "elegance", "elegant"],
    "Retail & E-Commerce": ["retail", "apparel", "shopping", "store", "threads", "e-commerce", "boutique", "mall", "outlet"],
    # Finance MUST come before Auto to avoid "auto-pay", "auto loan" matching Auto category
    "Finance & Insurance": [
        "bank", "banking", "finance", "financial", "insurance", "credit", "credit card", "loan", "mortgage",
        "wealth", "investment", "fintech", "payments", "pay", "synchrony", "capital one", "chase", "wells fargo",
        "american express", "amex", "visa", "mastercard", "discover", "citibank", "citi",
    ],
    "Auto": ["automotive", "suv", "car ", "cars", "truck", "motors", "dealership", "vehicle", "ford", "toyota", "honda", "chevrolet", "bmw", "mercedes", "audi"],
    "Health & Pharma": ["health", "wellness", "pharma", "fitness", "care", "medical", "vitamin"],
    "Tech & Wireless": ["tech", "wireless", "mobile", "software", "hardware", "device", "app", "digital"],
    "Travel & Hospitality": ["travel", "hotel", "hospitality", "vacation", "tourism", "resort", "airline"],
    "Sports & Fitness": ["sports", "fitness", "athletic", "athlete", "gym", "workout"],
    "CPG": [
        "cpg", "consumer packaged", "grocery", "household", "cleaning", "personal care",
        "beverage", "beverages", "drink", "drinks", "sparkling water", "mineral water", "soda", "soft drink",
        "topo chico", "lacroix", "perrier", "pellegrino", "san pellegrino", "coca-cola", "coca cola", "coke",
        "pepsi", "dr pepper", "sprite", "fanta", "mountain dew", "gatorade", "powerade", "vitaminwater",
        "body armor", "bodyarmor", "celsius", "red bull", "monster energy", "bang energy", "prime",
        "juice", "lemonade", "tea", "iced tea", "kombucha", "energy drink", "sports drink",
        "snack", "snacks", "chips", "crackers", "cookies", "candy", "chocolate", "gum",
        "cereal", "breakfast", "yogurt", "milk", "dairy", "cheese", "butter",
        "soap", "shampoo", "conditioner", "lotion", "deodorant", "toothpaste", "detergent", "laundry",
        "paper towel", "tissue", "toilet paper", "trash bags", "food", "frozen", "canned",
    ],
    "Home & DIY": ["home", "diy", "renovation", "furniture", "garden", "improvement"],
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
    """Infer primary advertising category using keyword heuristics.
    
    DEPRECATED: Use infer_category_with_llm() for accurate category detection.
    This function is kept for backward compatibility but should not be relied upon
    for production category detection.
    """
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "CPG"  # Default fallback


def infer_category_with_llm(brand_name: str, brief: str) -> str:
    """
    Use LLM to accurately detect the advertising category for a brand.
    
    This is the PRIMARY method for category detection. The LLM understands
    brand context and can correctly identify categories for well-known brands
    like Starbucks (Culinary & Dining), Fendi (Luxury & Fashion), 
    Verizon (Tech & Wireless), etc.
    
    PHASE 1 FIX #5: Uses BRAND_CATEGORY_OVERRIDES first for known edge cases
    like Whole Foods (Retail), Dunkin' (QSR), etc.
    
    Args:
        brand_name: The brand name (e.g., "Starbucks", "Fendi", "Verizon")
        brief: The campaign brief or context
        
    Returns:
        One of the 15 canonical RJM advertising categories
    """
    from app.config.settings import settings
    from app.services.rjm_vector_store import get_openai_client
    
    # NOTE: Overrides disabled to allow LLM to decide category freely
    
    # Get the canonical category list
    valid_categories = list(CATEGORY_PERSONA_MAP.keys())
    categories_list = "\n".join(f"- {cat}" for cat in valid_categories)
    
    # Build the LLM prompt with comprehensive edge case guidance
    system_prompt = f"""You are an advertising category classifier for RJM. Your job is to determine the correct advertising category for a brand based on its PRIMARY business model and the campaign brief.

VALID CATEGORIES (choose exactly one):
{categories_list}

═══════════════════════════════════════════════════════════════════════════════
CRITICAL CATEGORY GUIDANCE - READ CAREFULLY
═══════════════════════════════════════════════════════════════════════════════

FOOD DELIVERY PLATFORMS (this is important!):
- Uber Eats, DoorDash, Grubhub, Postmates, Instacart → QSR (not Culinary & Dining)
- These are QUICK SERVICE platforms focused on delivery/convenience, not sit-down dining
- If the brief mentions "delivery", "app", "doorstep", "order online" → lean QSR

FOOD & DINING:
- Culinary & Dining: Sit-down restaurants, coffee shops, cafes, food experiences (Starbucks, Hillstone, Cheesecake Factory)
- QSR: Fast food, quick service, drive-thru, delivery-first (McDonald's, Dunkin', Taco Bell, Chick-fil-A)

EDUCATION & TRAINING:
- University of Phoenix, Coursera, LinkedIn Learning, trade schools → B2B & Professional Services
- These serve adult learners and career development, not consumer packaged goods

POLITICAL / CIVIC / VOTER CAMPAIGNS (IMPORTANT!):
- Political candidates, voter campaigns, ballot initiatives → CPG (NOT B2B)
- These target VOTERS (consumers), not businesses
- Congressional, mayoral, gubernatorial, local elections → CPG
- The audience is everyday citizens, not enterprise buyers
- Do NOT classify political campaigns as B2B & Professional Services

LOCAL SERVICES & SMALL BUSINESSES:
- Pet services (dog walking, grooming, vet), local trades, community services → CPG or Retail & E-Commerce
- Focus on the SERVICE being offered to local consumers

GROCERY & SUPERMARKETS:
- Whole Foods, Trader Joe's, Kroger, Costco → Retail & E-Commerce (not CPG)
- They SELL CPG products but they ARE retailers

RIDESHARE & TRANSPORTATION:
- Uber (rides), Lyft → Tech & Wireless or Travel & Hospitality
- These are tech platforms, not food companies

OTHER GUIDANCE:
- Luxury & Fashion: High-end fashion, luxury goods, designer brands (Fendi, Gucci, Louis Vuitton)
- Tech & Wireless: Telecom, mobile carriers, technology companies (Verizon, Apple, Samsung)
- Sports & Fitness: Fitness equipment, athletic brands, gyms (Peloton, Nike, Equinox)
- Finance & Insurance: Banks, credit cards, insurance (Chase, Amex, State Farm)
- Auto: Car manufacturers, dealerships (Ford, Toyota, BMW)
- Entertainment: Streaming, media, gaming (Netflix, Disney, Spotify, Xbox)
- Travel & Hospitality: Hotels, airlines, travel services (Marriott, Delta, Airbnb)
- Health & Pharma: Healthcare, pharmaceuticals, wellness brands
- Home & DIY: Home improvement, furniture, home goods
- Alcohol & Spirits: Beer, wine, spirits brands
- CPG: Consumer packaged goods, grocery items, household products (Tide, Clorox, Kraft)

RESPOND WITH ONLY THE CATEGORY NAME, nothing else."""

    user_prompt = f"""Brand: {brand_name}
Brief: {brief}

What is the correct advertising category for this brand?"""

    try:
        client = get_openai_client()
        completion = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=0,  # Deterministic for consistency
            max_tokens=50,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        
        response = completion.choices[0].message.content.strip()
        
        # Validate the response is a valid category
        for category in valid_categories:
            if category.lower() == response.lower() or category.lower() in response.lower():
                app_logger.info(f"LLM category detection: '{brand_name}' -> '{category}'")
                return category
        
        # If no exact match, try to find the best match
        response_lower = response.lower()
        for category in valid_categories:
            # Check if category name appears in response
            cat_lower = category.lower()
            if cat_lower in response_lower:
                app_logger.info(f"LLM category detection (partial match): '{brand_name}' -> '{category}'")
                return category
        
        # Fallback to keyword-based if LLM response is unexpected
        app_logger.warning(f"LLM returned unexpected category '{response}' for brand '{brand_name}', falling back to keyword detection")
        return infer_category(f"{brand_name} {brief}")
        
    except Exception as exc:
        app_logger.error(f"LLM category detection failed for '{brand_name}': {exc}")
        # Fallback to keyword-based detection
        return infer_category(f"{brand_name} {brief}")


def get_brand_categories(brand_name: str) -> List[str]:
    """Return list of categories for a brand (handles dual-anchor brands)."""
    lowered = brand_name.lower().strip()
    if lowered in DUAL_ANCHOR_BRANDS:
        return DUAL_ANCHOR_BRANDS[lowered]
    return []


def analyze_brand_context(brand_name: str, brief: str, category: str) -> Dict[str, Any]:
    """
    Use LLM to deeply understand the brand context BEFORE persona selection.
    
    This is the KEY FIX for the "sequencing problem" Jesse identified:
    - The system was deciding WHO the audience is before understanding WHAT the product/service is
    - Now we understand the brand FIRST, then let persona selection follow the meaning
    
    This replaces all hardcoded heuristics (detect_meaning_tags, get_flexible_persona_pool prepending)
    with intelligent LLM-based brand understanding.
    
    Returns a dict with:
    - audience_type: "consumer" | "b2b" | "civic" | "mixed"
    - persona_guidance: LLM-generated guidance for persona selection
    - avoid_personas: List of persona types to avoid
    - prioritize_personas: List of persona types to prioritize
    """
    from app.config.settings import settings
    from app.services.rjm_vector_store import get_openai_client
    
    system_prompt = """You are an expert brand strategist analyzing a brand to guide persona selection.
Your job is to understand WHAT the brand/service actually is and WHO the real audience is.

CRITICAL CLASSIFICATION RULES:

1. POLITICAL/CIVIC CAMPAIGNS (Congress, Senate, Mayor, Governor, ballot measures, political candidates):
   - audience_type: MUST be "civic"
   - PRIORITIZE: Neighborhood Watch, Volunteer, Faith, Hometown Hero, Main Street, PTA, Mayor
   - AVOID: Budget-Minded, Bargain Hunter, Savvy Shopper, Gifter (these are shopping personas)
   - Voters are CONSTITUENTS, not shoppers

2. PET SERVICES (dog walking, pet grooming, pet sitting, veterinary, pet care):
   - audience_type: "pet_service"
   - PRIORITIZE: Dog Parent, Pack Leader, Pawrent, Rescuer, Petfluencer, Best in Show
   - AVOID: Budget-Minded, Bargain Hunter, Savvy Shopper as HIGHLIGHTS (ok in portfolio)
   - Pet owners define themselves by their relationship with pets

3. FITNESS/WELLNESS BRANDS (gyms, fitness studios, workout apps):
   - audience_type: "fitness"
   - PRIORITIZE: Gym Obsessed, Elite Competitor, Sculpt, Biohacker, Weekend Warrior
   - AVOID: Neighborhood Watch, Volunteer, PTA (civic personas don't fit fitness)

4. HEALTH SUPPLEMENTS (vitamins, gut health, wellness products):
   - audience_type: "wellness"
   - PRIORITIZE: Biohacker, Clean Eats, Self-Love, Detox, Modern Monk
   - AVOID: Civic personas like Neighborhood Watch, Volunteer

5. EDUCATION/TRAINING (universities, online learning, courses):
   - audience_type: "learner"
   - PRIORITIZE: Scholar, Planner, Mentor, Coach, Self-Love, Digital Nomad
   - AVOID: Power Broker, Boss, Disruptor unless targeting executives

6. SPORTS TEAMS (NBA, NFL, MLB teams, ticket sales):
   - audience_type: "sports"
   - PRIORITIZE: Elite Competitor, Weekend Warrior, Basketball Junkie, Sports Parent, Fantasy GM
   - This is correct, no changes needed

Respond in JSON format:
{
  "brand_understanding": "1-2 sentence description of what this brand/service actually is",
  "audience_type": "consumer" | "civic" | "pet_service" | "fitness" | "wellness" | "learner" | "sports",
  "persona_guidance": "Clear guidance for persona selection",
  "prioritize_personas": ["specific persona names to use"],
  "avoid_personas": ["specific persona names to avoid"]
}"""

    user_prompt = f"""Brand: {brand_name}
Category: {category}
Brief: {brief}

Analyze this brand and provide persona selection guidance."""

    try:
        client = get_openai_client()
        completion = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=0.1,  # Low temperature for consistency
            max_tokens=500,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        
        response = completion.choices[0].message.content.strip()
        
        # Parse JSON response
        import json
        # Handle potential markdown code blocks
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        
        result = json.loads(response)
        app_logger.info(
            f"Brand context analysis for '{brand_name}': "
            f"audience_type={result.get('audience_type')}, "
            f"prioritize={result.get('prioritize_personas', [])[:3]}"
        )
        return result
        
    except Exception as exc:
        app_logger.warning(f"Brand context analysis failed for '{brand_name}': {exc}")
        # Return neutral guidance if LLM fails
        return {
            "brand_understanding": f"{brand_name} campaign",
            "audience_type": "consumer",
            "persona_guidance": "Select personas that match the category and brief meaning",
            "prioritize_personas": [],
            "avoid_personas": [],
        }


def detect_meaning_tags(brand_name: str, brief: str) -> Set[str]:
    """
    DEPRECATED: This function has been disabled to prevent hardcoded heuristics
    from causing persona selection issues (civic bleed, wrong persona clusters).
    
    The LLM now handles all brand understanding and persona selection through
    the analyze_brand_context() function which makes intelligent decisions
    based on the actual meaning of the brief, not keyword matching.
    
    Returns an empty set. Brand understanding is now handled by LLM calls.
    """
    # All meaning detection is now handled by LLM in analyze_brand_context()
    # This prevents false positives like "community fitness" triggering civic personas
    return set()


def get_flexible_persona_pool(category: str, brand_name: str, brief: str) -> List[str]:
    """
    Build a category persona pool.
    
    SIMPLIFIED VERSION: Returns the pure category pool without hardcoded prepending.
    The LLM is now responsible for intelligent persona selection based on the
    analyze_brand_context() function which understands the brand's meaning.
    
    This prevents:
    - Civic personas bleeding into fitness brands
    - Budget-Minded cluster appearing in wrong categories
    - Community personas appearing in individual-focused brands
    
    The LLM receives the category pool and selects personas that match the
    MEANING expressed in the brief and write-ups, guided by prompts, not heuristics.
    """
    # Start with pure category pool
    base_pool = list(CATEGORY_PERSONA_MAP.get(category, []))
    
    # Dual-anchor: union both category pools (for known dual-category brands like Uber)
    dual_categories = DUAL_ANCHOR_BRANDS.get(brand_name.lower().strip(), [])
    for dual_cat in dual_categories:
        if dual_cat != category:
            base_pool.extend(CATEGORY_PERSONA_MAP.get(dual_cat, []))
    
    # Deduplicate while preserving order
    seen: Set[str] = set()
    deduped: List[str] = []
    for name in base_pool:
        if name not in seen:
            seen.add(name)
            deduped.append(name)
    
    return deduped


def get_category_personas(category: str) -> List[str]:
    """Return persona names for a given advertising category."""
    return CATEGORY_PERSONA_MAP.get(category, [])


def is_persona_valid_for_category(persona_name: str, category: str) -> bool:
    """
    Check if a persona is valid for a given category.

    This is the PRIMARY SELECTOR from the Ingredient Canon 11.26.25.
    A persona must be in the category's persona pool to be valid.

    This prevents wrong-fit personas like:
    - "Bargain Hunter" for Luxury & Fashion (INVALID)
    - "Budget-Minded" for Luxury & Fashion (INVALID)

    Args:
        persona_name: The persona name to check
        category: The advertising category

    Returns:
        True if persona is valid for category, False otherwise
    """
    if not persona_name or not category:
        return False

    # Get the category's persona pool
    category_personas = CATEGORY_PERSONA_MAP.get(category, [])
    if not category_personas:
        # Unknown category - fall back to canon check only
        return is_canon_persona(persona_name)

    # Normalize persona name for matching
    canonical_name = get_canonical_name(persona_name)

    # Build normalized set of category personas for matching
    normalized_category_personas = set()
    for p in category_personas:
        normalized_category_personas.add(p.lower())
        normalized_category_personas.add(_normalize_persona_name(p).lower())

    # Check if persona is in category pool
    if canonical_name.lower() in normalized_category_personas:
        return True
    if _normalize_persona_name(canonical_name).lower() in normalized_category_personas:
        return True
    if persona_name.lower() in normalized_category_personas:
        return True

    return False


def get_invalid_personas_for_category(persona_names: List[str], category: str) -> List[str]:
    """
    Return list of personas that are NOT valid for a given category.

    Useful for debugging and logging which personas were rejected.
    """
    invalid = []
    for name in persona_names:
        if not is_persona_valid_for_category(name, category):
            invalid.append(name)
    return invalid


def filter_personas_by_category(persona_names: List[str], category: str) -> List[str]:
    """
    Filter a list of personas to only include those valid for the category.

    This is used to enforce the Category → Persona Map as the primary selector.
    """
    return [name for name in persona_names if is_persona_valid_for_category(name, category)]


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
    """Check if a persona name is in the canon (handles name variations).
    
    PHASE 1 FIX #3: Also rejects deprecated/sunset personas.
    The canon acts as a STRICT ALLOWLIST - only active personas are valid.
    """
    if not name:
        return False
    
    # PHASE 1 FIX #3: Check if persona is deprecated
    if name in DEPRECATED_PERSONAS:
        app_logger.debug(f"Rejected deprecated persona: {name}")
        return False
    
    # Also check normalized form against deprecated list
    normalized = _normalize_persona_name(name)
    for deprecated in DEPRECATED_PERSONAS:
        if _normalize_persona_name(deprecated).lower() == normalized.lower():
            app_logger.debug(f"Rejected deprecated persona (normalized match): {name}")
            return False
    
    # Direct match
    if name in _ALL_CANON_PERSONAS:
        return True
    # Try normalized matching
    return normalized.lower() in _NORMALIZED_CANON_MAP


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


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1 ENFORCEMENT FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def is_deprecated_persona(name: str) -> bool:
    """Check if a persona is deprecated/sunset (Phase 1 Fix #3).
    
    Deprecated personas MUST NOT appear in any generated programs.
    """
    if name in DEPRECATED_PERSONAS:
        return True
    # Also check normalized form
    normalized = _normalize_persona_name(name).lower()
    for deprecated in DEPRECATED_PERSONAS:
        if _normalize_persona_name(deprecated).lower() == normalized:
            return True
    return False


def validate_persona_strict(name: str, category: str) -> Tuple[bool, Optional[str]]:
    """Strict validation for a persona (Phase 1 Fix #3).
    
    Returns (is_valid, error_message).
    A persona is valid if:
    1. It is NOT deprecated
    2. It IS in the canon
    3. It IS valid for the category
    """
    if not name:
        return False, "Empty persona name"
    
    # Check deprecated first
    if is_deprecated_persona(name):
        return False, f"'{name}' is a deprecated/sunset persona"
    
    # Check canon
    if not is_canon_persona(name):
        return False, f"'{name}' is not in the RJM canon"
    
    # Check category fit
    if not is_persona_valid_for_category(name, category):
        return False, f"'{name}' is not valid for category '{category}'"
    
    return True, None


def select_personas_with_rotation(
    pool: List[str],
    category: str,
    count: int,
    exclude: Optional[Set[str]] = None,
    prefer_fresh: bool = True,
) -> List[str]:
    """Select personas from pool with rotation pressure applied (Phase 1 Fix #1).
    
    This function applies weighted selection to avoid "default persona gravity"
    where the same obvious personas keep appearing.
    
    Args:
        pool: List of candidate personas
        category: Advertising category for hot persona detection
        count: Number of personas to select
        exclude: Set of personas to exclude
        prefer_fresh: Whether to apply freshness weighting
    
    Returns:
        Selected personas in priority order
    """
    exclude_set = exclude or set()
    candidates = []
    
    for name in pool:
        if name in exclude_set:
            continue
        
        # Skip deprecated
        if is_deprecated_persona(name):
            continue
        
        # Calculate weight
        recency_pos = -1
        if prefer_fresh and name in _RECENT_PERSONAS:
            recency_pos = list(_RECENT_PERSONAS).index(name)
        
        weight = get_rotation_weight(name, category, recency_pos)
        candidates.append((name, weight))
    
    # Sort by weight (highest first) with randomization for equal weights
    candidates.sort(key=lambda x: (-x[1], random.random()))
    
    # Select top candidates
    selected = [name for name, _ in candidates[:count]]
    
    return selected


def select_highlights_with_rotation(
    personas: List[str],
    category: str,
    count: int = 3,
    exclude_from_insights: bool = True,
) -> Tuple[List[str], Set[str]]:
    """Select highlight personas with rotation pressure (Phase 1 Fix #1 & #2).
    
    Returns (highlight_personas, insight_exclusion_set).
    
    The insight_exclusion_set contains all highlight personas that MUST NOT
    appear in insights (Phase 1 Fix #2: hard separation).
    """
    selected = select_personas_with_rotation(
        pool=personas,
        category=category,
        count=count,
        prefer_fresh=True,
    )
    
    # PHASE 1 FIX #2: Build exclusion set for insights
    insight_exclusion = set(selected) if exclude_from_insights else set()
    
    return selected, insight_exclusion


def select_insights_personas(
    pool: List[str],
    category: str,
    count: int = 2,
    exclude: Optional[Set[str]] = None,
) -> List[str]:
    """Select personas for insights, ensuring separation from highlights (Phase 1 Fix #2).
    
    CRITICAL: The exclude set MUST contain all highlight personas.
    This enforces hard separation between highlights and insights.
    """
    if exclude is None:
        exclude = set()
    
    # Validate that we have candidates
    available = [p for p in pool if p not in exclude]
    
    if not available:
        app_logger.warning(
            f"No personas available for insights after excluding {len(exclude)} highlights. "
            "This may indicate an issue with portfolio size."
        )
        # Fall back to pool minus first 3 (likely highlights)
        available = pool[3:] if len(pool) > 3 else pool
    
    return select_personas_with_rotation(
        pool=available,
        category=category,
        count=count,
        exclude=exclude,
        prefer_fresh=True,
    )


def get_category_override(brand_name: str) -> Optional[str]:
    """Get category override for a brand if one exists (Phase 1 Fix #5)."""
    brand_lower = brand_name.lower().strip()
    return BRAND_CATEGORY_OVERRIDES.get(brand_lower)


# Log initialization
app_logger.info(
    f"RJM Ingredient Canon 11.26.25 loaded: "
    f"{len(CATEGORY_PERSONA_MAP)} categories, "
    f"{len(PHYLUM_PERSONA_MAP)} phyla, "
    f"{len(GENERATIONS)} generations, "
    f"{len(MULTICULTURAL_EXPRESSIONS)} multicultural expressions, "
    f"{len(LOCAL_CULTURE_DMAS)} DMA segments, "
    f"{len(DEPRECATED_PERSONAS)} deprecated personas, "
    f"{len(BRAND_CATEGORY_OVERRIDES)} brand overrides"
)

