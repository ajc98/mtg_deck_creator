"""Role-aware Commander deck construction algorithm."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from mtgdeck.rules.commander_rules import CommanderProfile
from mtgdeck.scoring.card_score import CardScore, ScoreWeights, score_card
from mtgdeck.scoring.role_classifier import (
    DRAW_ROLES, LAND_ROLES, RAMP_ROLES,
    ROLE_BOARD_WIPE, ROLE_COUNTERSPELL, ROLE_PROTECTION,
    ROLE_REMOVAL, ROLE_WIN_CONDITION,
    classify_card, primary_role,
)

# ── Colour → basic land name ─────────────────────────────────────────────────
_COLOR_TO_BASIC: dict[str, str] = {
    "W": "Plains",
    "U": "Island",
    "B": "Swamp",
    "R": "Mountain",
    "G": "Forest",
}


@dataclass
class DeckConfig:
    commander_name: str
    num_lands: int = 36
    owned_only: bool = False
    budget: float | None = None
    model_alias: str = "local"


@dataclass
class BuiltDeck:
    deck_id: str
    commander_name: str
    commander_row: dict
    cards: list[dict]            # 99 card rows
    card_scores: list[CardScore]
    role_counts: dict[str, int]
    warnings: list[str] = field(default_factory=list)


# ── Role bucket definitions ──────────────────────────────────────────────────
# Each bucket: which roles satisfy it, and how many slots to fill
_BUCKETS: list[dict] = [
    {"name": "land",         "roles": LAND_ROLES,                    "target": 36},
    {"name": "ramp",         "roles": RAMP_ROLES,                    "target": 10},
    {"name": "card_draw",    "roles": DRAW_ROLES,                    "target": 10},
    {"name": "removal",      "roles": {ROLE_REMOVAL},                "target": 7},
    {"name": "board_wipe",   "roles": {ROLE_BOARD_WIPE},             "target": 3},
    {"name": "protection",   "roles": {ROLE_PROTECTION},             "target": 3},
    {"name": "win_condition","roles": {ROLE_WIN_CONDITION},          "target": 4},
]

# Flat map of role → target count (for role_need scoring)
_ROLE_TARGETS: dict[str, int] = {}
for _b in _BUCKETS:
    for _r in _b["roles"]:
        _ROLE_TARGETS[_r] = _b["target"]


def _bucket_target(bucket_name: str, config: DeckConfig) -> int:
    if bucket_name == "land":
        return config.num_lands
    for b in _BUCKETS:
        if b["name"] == bucket_name:
            return b["target"]
    return 0


def _role_sort_key(candidate, bucket_roles: set[str]) -> float:
    rec = candidate.edhrec_rec
    edhrec = 0.0
    if rec:
        edhrec = float(rec.get("deck_percentage") or 0) / 100.0
    return edhrec + candidate.vector_score * 0.5


def _basic_land_name(color_identity: list[str]) -> str:
    if not color_identity:
        return "Wastes"
    for c in ("B", "G", "R", "U", "W"):  # favour least-common first for variety
        if c in color_identity:
            return _COLOR_TO_BASIC[c]
    return "Wastes"


def _basic_land_names_for_ci(color_identity: list[str], count: int) -> list[str]:
    """Return *count* basic land names distributed across the commander's colours."""
    if not color_identity:
        return ["Wastes"] * count
    colours = [c for c in color_identity if c in _COLOR_TO_BASIC]
    if not colours:
        return ["Wastes"] * count
    basics: list[str] = []
    for i in range(count):
        basics.append(_COLOR_TO_BASIC[colours[i % len(colours)]])
    return basics


# ── Main builder ─────────────────────────────────────────────────────────────


def build_deck(
    conn: duckdb.DuckDBPyConnection,
    profile: CommanderProfile,
    candidates,            # list[CandidateCard]
    config: DeckConfig,
) -> BuiltDeck:
    """Build a 99-card deck (+ commander = 100) from a scored candidate pool.

    Algorithm:
    1. Fill mandatory role buckets (lands, ramp, draw, removal, wipes, protection, wincons).
    2. Fill remaining slots with highest-scoring synergy candidates.
    3. Backfill with basic lands if still short.
    4. Score every included card for the explanation report.
    """
    from mtgdeck.data.duckdb_repo import get_card_by_normalized_name, save_generated_deck, save_card_scores

    commander_ci = profile.color_identity
    weights      = ScoreWeights()

    used: set[str]          = set()   # card names already placed
    deck_cards: list[dict]  = []
    deck_scores: list[CardScore] = []
    role_counts: dict[str, int]  = {b["name"]: 0 for b in _BUCKETS}
    role_counts["synergy"] = 0

    current_role_counts: dict[str, int] = {}

    # ── Phase 1: mandatory buckets ───────────────────────────────────────────
    for bucket in _BUCKETS:
        bname  = bucket["name"]
        broles = bucket["roles"]
        target = _bucket_target(bname, config)

        eligible = [
            c for c in candidates
            if any(r in broles for r in c.roles) and c.name not in used
        ]
        eligible.sort(key=lambda c: _role_sort_key(c, broles), reverse=True)

        for candidate in eligible[:target]:
            cs = score_card(candidate, current_role_counts, _ROLE_TARGETS, weights)
            deck_cards.append(candidate.card_row)
            deck_scores.append(cs)
            used.add(candidate.name)
            role_counts[bname] += 1
            for r in candidate.roles:
                current_role_counts[r] = current_role_counts.get(r, 0) + 1

    # ── Phase 2: synergy fill ────────────────────────────────────────────────
    remaining = 99 - len(deck_cards)
    if remaining > 0:
        synergy_pool = [c for c in candidates if c.name not in used]
        synergy_pool.sort(
            key=lambda c: score_card(c, current_role_counts, _ROLE_TARGETS, weights).final_score,
            reverse=True,
        )
        for candidate in synergy_pool[:remaining]:
            cs = score_card(candidate, current_role_counts, _ROLE_TARGETS, weights)
            deck_cards.append(candidate.card_row)
            deck_scores.append(cs)
            used.add(candidate.name)
            role_counts["synergy"] += 1
            for r in candidate.roles:
                current_role_counts[r] = current_role_counts.get(r, 0) + 1

    # ── Phase 3: basic land backfill ─────────────────────────────────────────
    while len(deck_cards) < 99:
        basic_name = _basic_land_name(commander_ci)
        basic_row  = get_card_by_normalized_name(conn, basic_name.lower())
        if basic_row is None:
            # DB not loaded yet — create a minimal placeholder row
            basic_row = {
                "name": basic_name,
                "normalized_name": basic_name.lower(),
                "type_line": f"Basic Land — {basic_name}",
                "oracle_text": "",
                "cmc": 0.0,
                "color_identity": "[]",
                "is_land": True,
                "is_basic_land": True,
            }
        deck_cards.append(basic_row)
        role_counts["land"] = role_counts.get("land", 0) + 1

    # ── Phase 4: compute warnings ─────────────────────────────────────────────
    warnings: list[str] = []
    land_count = sum(1 for c in deck_cards if c.get("is_land"))
    ramp_count = role_counts.get("ramp", 0)
    draw_count = role_counts.get("card_draw", 0)
    if land_count < 33:
        warnings.append(f"Only {land_count} lands — consider adding more.")
    if ramp_count < 7:
        warnings.append(f"Only {ramp_count} ramp cards — decks typically need 8–12.")
    if draw_count < 7:
        warnings.append(f"Only {draw_count} card draw effects — decks typically need 8–12.")

    # ── Persist ──────────────────────────────────────────────────────────────
    deck_id    = str(uuid.uuid4())
    deck_names = [profile.commander_name if hasattr(profile, "commander_name") else profile.card.name] + [
        c.get("name", "") for c in deck_cards
    ]
    config_j   = json.dumps({"commander": config.commander_name, "num_lands": config.num_lands})
    deck_j     = json.dumps(deck_names)

    save_generated_deck(conn, deck_id, config.commander_name, config_j, deck_j, "")
    save_card_scores(conn, deck_id, deck_scores)

    return BuiltDeck(
        deck_id=deck_id,
        commander_name=config.commander_name,
        commander_row=get_card_by_normalized_name(conn, profile.card.normalized_name) or {},
        cards=deck_cards,
        card_scores=deck_scores,
        role_counts=role_counts,
        warnings=warnings,
    )
