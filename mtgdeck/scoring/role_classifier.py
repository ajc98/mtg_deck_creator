"""Oracle-text pattern-based card role classifier."""
from __future__ import annotations

import re

from mtgdeck.models import BASIC_LAND_NAMES

# ── Role string constants ────────────────────────────────────────────────────
ROLE_BASIC_LAND      = "basic_land"
ROLE_LAND            = "land"
ROLE_MANA_ROCK       = "mana_rock"
ROLE_MANA_DORK       = "mana_dork"
ROLE_LAND_RAMP       = "land_ramp"
ROLE_CARD_DRAW       = "card_draw"
ROLE_TUTOR           = "tutor"
ROLE_REMOVAL         = "removal"
ROLE_BOARD_WIPE      = "board_wipe"
ROLE_COUNTERSPELL    = "counterspell"
ROLE_PROTECTION      = "protection"
ROLE_RECURSION       = "recursion"
ROLE_GRAVEYARD_HATE  = "graveyard_hate"
ROLE_SACRIFICE_OUTLET = "sacrifice_outlet"
ROLE_TOKEN_PRODUCER  = "token_producer"
ROLE_LIFEGAIN        = "lifegain"
ROLE_WIN_CONDITION   = "win_condition"
ROLE_SYNERGY         = "synergy"

# Sets for bucket membership checks
RAMP_ROLES        = {ROLE_MANA_ROCK, ROLE_MANA_DORK, ROLE_LAND_RAMP}
DRAW_ROLES        = {ROLE_CARD_DRAW, ROLE_TUTOR}
INTERACTION_ROLES = {ROLE_REMOVAL, ROLE_BOARD_WIPE, ROLE_COUNTERSPELL}
LAND_ROLES        = {ROLE_LAND, ROLE_BASIC_LAND}

# Human-readable labels
ROLE_LABELS: dict[str, str] = {
    ROLE_BASIC_LAND:       "Basic Land",
    ROLE_LAND:             "Land",
    ROLE_MANA_ROCK:        "Mana Rock",
    ROLE_MANA_DORK:        "Mana Dork",
    ROLE_LAND_RAMP:        "Land Ramp",
    ROLE_CARD_DRAW:        "Card Draw",
    ROLE_TUTOR:            "Tutor",
    ROLE_REMOVAL:          "Removal",
    ROLE_BOARD_WIPE:       "Board Wipe",
    ROLE_COUNTERSPELL:     "Counterspell",
    ROLE_PROTECTION:       "Protection",
    ROLE_RECURSION:        "Recursion",
    ROLE_GRAVEYARD_HATE:   "Graveyard Hate",
    ROLE_SACRIFICE_OUTLET: "Sacrifice Outlet",
    ROLE_TOKEN_PRODUCER:   "Token Producer",
    ROLE_LIFEGAIN:         "Lifegain",
    ROLE_WIN_CONDITION:    "Win Condition",
    ROLE_SYNERGY:          "Synergy",
}

# ── Patterns: (role, regex_string, flags) ────────────────────────────────────
_PATTERNS: list[tuple[str, str, int]] = [
    # Land ramp
    (ROLE_LAND_RAMP, r"search your library for (a|an|up to \d+) .{0,40}(land|plains|island|swamp|mountain|forest|wastes)\b", re.I),
    (ROLE_LAND_RAMP, r"put (a|that) .{0,20}(land|plains|island|swamp|mountain|forest) card .{0,30}(onto the battlefield|into your hand)", re.I),

    # Card draw
    (ROLE_CARD_DRAW, r"draw (a|an|\d+|x|two|three|four|five|six|seven) cards?", re.I),
    (ROLE_CARD_DRAW, r"draw that many cards", re.I),
    (ROLE_CARD_DRAW, r"draw cards equal", re.I),
    (ROLE_CARD_DRAW, r"(target player|each player|you) draw", re.I),

    # Tutors (search for non-land cards)
    (ROLE_TUTOR, r"search your library for (a|an|up to) (?!.{0,10}(basic|land))\w", re.I),

    # Single-target removal
    (ROLE_REMOVAL, r"destroy target (?!all|each|every|player|opponent)", re.I),
    (ROLE_REMOVAL, r"exile target (creature|artifact|enchantment|permanent|nonland|planeswalker|instant|sorcery)", re.I),
    (ROLE_REMOVAL, r"return target\b.{0,60}\bto (its|their) owner'?s? hand", re.I),
    (ROLE_REMOVAL, r"deals? \d+ damage to (target creature|any target)", re.I),
    (ROLE_REMOVAL, r"target .{0,30}gets? -\d+/-\d+", re.I),

    # Board wipes
    (ROLE_BOARD_WIPE, r"destroy all (creatures?|permanents?|nonland permanents?)", re.I),
    (ROLE_BOARD_WIPE, r"exile all (creatures?|permanents?|artifacts?|enchantments?|nonland permanents?)", re.I),
    (ROLE_BOARD_WIPE, r"each creature gets? -\d+/-\d+ until", re.I),
    (ROLE_BOARD_WIPE, r"return all (creatures|permanents) .{0,30}to (their owners|hand)", re.I),
    (ROLE_BOARD_WIPE, r"deals? \d+ damage to (all creatures|each creature)", re.I),
    (ROLE_BOARD_WIPE, r"each player sacrifices .{0,20}creatures?", re.I),

    # Counterspells
    (ROLE_COUNTERSPELL, r"counter target (spell|activated ability|triggered ability|ability)", re.I),

    # Protection
    (ROLE_PROTECTION, r"\bhexproof\b", re.I),
    (ROLE_PROTECTION, r"\bindestructible\b", re.I),
    (ROLE_PROTECTION, r"\bshroud\b", re.I),
    (ROLE_PROTECTION, r"\bward \{", re.I),
    (ROLE_PROTECTION, r"protection from", re.I),
    (ROLE_PROTECTION, r"can't be (countered|targeted by)", re.I),
    (ROLE_PROTECTION, r"phases? out", re.I),

    # Recursion
    (ROLE_RECURSION, r"return (target|up to \d+) .{0,60}(from|in) (a|your|their) graveyard", re.I),
    (ROLE_RECURSION, r"return all .{0,30}from (a|your|their) graveyard", re.I),

    # Graveyard hate
    (ROLE_GRAVEYARD_HATE, r"exile .{0,30}cards? from .{0,40}graveyards?", re.I),
    (ROLE_GRAVEYARD_HATE, r"each player exiles? .{0,20}graveyard", re.I),

    # Sacrifice outlets
    (ROLE_SACRIFICE_OUTLET, r"sacrifice (a|another|any number of) (creature|permanent|artifact|enchantment|land)s? ?[,:]", re.I),

    # Token producers
    (ROLE_TOKEN_PRODUCER, r"create (a|an|\d+|x) .{0,50}token", re.I),
    (ROLE_TOKEN_PRODUCER, r"put (a|an|\d+|x|two|three|four|five|six) .{0,50}tokens? .{0,30}(onto the battlefield|into play)", re.I),

    # Lifegain
    (ROLE_LIFEGAIN, r"(you |target player |each player )?gains? (\d+|x) life", re.I),

    # Win conditions
    (ROLE_WIN_CONDITION, r"\binfect\b", re.I),
    (ROLE_WIN_CONDITION, r"each opponent (loses?|takes?) (\d+|x) (life|damage)", re.I),
    (ROLE_WIN_CONDITION, r"deals? (\d+|x) damage to each opponent", re.I),
    (ROLE_WIN_CONDITION, r"you win the game", re.I),
    (ROLE_WIN_CONDITION, r"opponent?s? lose the game", re.I),
    (ROLE_WIN_CONDITION, r"target player loses the game", re.I),
]

# Priority order for primary role selection (first match wins)
_PRIORITY: list[str] = [
    ROLE_BASIC_LAND,
    ROLE_LAND,
    ROLE_MANA_ROCK,
    ROLE_MANA_DORK,
    ROLE_LAND_RAMP,
    ROLE_TUTOR,
    ROLE_BOARD_WIPE,
    ROLE_COUNTERSPELL,
    ROLE_RECURSION,
    ROLE_REMOVAL,
    ROLE_CARD_DRAW,
    ROLE_PROTECTION,
    ROLE_WIN_CONDITION,
    ROLE_SACRIFICE_OUTLET,
    ROLE_TOKEN_PRODUCER,
    ROLE_GRAVEYARD_HATE,
    ROLE_LIFEGAIN,
    ROLE_SYNERGY,
]


def classify_card(card: dict) -> list[str]:
    """Return all role tags for a card dict from the DB (or any dict with the right keys)."""
    roles: set[str] = set()
    name: str = card.get("name", "")
    oracle: str = card.get("oracle_text", "") or ""
    is_creature: bool = bool(card.get("is_creature"))
    is_artifact: bool = bool(card.get("is_artifact"))
    is_land: bool = bool(card.get("is_land"))

    if name in BASIC_LAND_NAMES:
        return [ROLE_BASIC_LAND, ROLE_LAND]

    if is_land:
        roles.add(ROLE_LAND)

    # Mana rock: non-creature artifact that taps/produces mana
    if is_artifact and not is_creature:
        if re.search(r"\badd \{|\{T\}[^.]*\badd\b", oracle, re.I):
            roles.add(ROLE_MANA_ROCK)

    # Mana dork: creature that produces mana
    if is_creature:
        if re.search(r"\badd \{|\{T\}[^.]*\badd\b", oracle, re.I):
            roles.add(ROLE_MANA_DORK)

    # Pattern-based roles
    for role, pattern, flags in _PATTERNS:
        if re.search(pattern, oracle, flags):
            roles.add(role)

    # Fallback
    if not roles:
        roles.add(ROLE_SYNERGY)

    return sorted(roles)


def primary_role(roles: list[str]) -> str:
    """Return the highest-priority role from a list."""
    for r in _PRIORITY:
        if r in roles:
            return r
    return ROLE_SYNERGY


def role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role.replace("_", " ").title())
