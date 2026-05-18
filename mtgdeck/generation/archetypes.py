"""Archetype detection and dynamic bucket definitions for Commander deckbuilding.

Archetypes add mandatory role buckets on top of the baseline buckets.
This ensures sacrifice commanders get sac outlets, death triggers, etc.
even when those cards share no oracle text with the commander.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from mtgdeck.scoring.role_classifier import (
    ROLE_BOARD_WIPE,
    ROLE_CARD_DRAW,
    ROLE_COMBAT_TRIGGER,
    ROLE_COST_REDUCER,
    ROLE_COUNTERSPELL,
    ROLE_DEATH_TRIGGER,
    ROLE_EXTRA_COMBAT,
    ROLE_GRAVEYARD_HATE,
    ROLE_HASTE_ENABLER,
    ROLE_LEAVES_BATTLEFIELD,
    ROLE_MANA_DORK,
    ROLE_MANA_ROCK,
    ROLE_PROTECTION,
    ROLE_RECURSION,
    ROLE_REMOVAL,
    ROLE_SACRIFICE_OUTLET,
    ROLE_TOKEN_DOUBLER,
    ROLE_TOKEN_PRODUCER,
    ROLE_WIN_CONDITION,
)

# ── Archetype constants ───────────────────────────────────────────────────────

ARCH_SACRIFICE      = "sacrifice"
ARCH_TOKENS         = "tokens"
ARCH_GRAVEYARD      = "graveyard"
ARCH_SPELLSLINGER   = "spellslinger"
ARCH_DRAGONS        = "dragons"
ARCH_VOLTRON        = "voltron"
ARCH_COMBAT         = "combat"
ARCH_COUNTERS       = "+1/+1 counters"
ARCH_TRIBAL         = "tribal"


@dataclass
class ArchetypeBucket:
    """Extra mandatory role bucket added by an archetype."""
    name: str
    roles: set[str]
    target: int


@dataclass
class Archetype:
    name: str
    extra_buckets: list[ArchetypeBucket] = field(default_factory=list)
    # role → multiplier applied to role_need_score during synergy fill (Tier B)
    role_boosts: dict[str, float] = field(default_factory=dict)


# ── Archetype definitions ─────────────────────────────────────────────────────

_ARCHETYPES: dict[str, Archetype] = {
    ARCH_SACRIFICE: Archetype(
        name=ARCH_SACRIFICE,
        extra_buckets=[
            ArchetypeBucket("sac_outlets",     {ROLE_SACRIFICE_OUTLET},            target=5),
            ArchetypeBucket("death_triggers",   {ROLE_DEATH_TRIGGER},               target=6),
            ArchetypeBucket("token_producers",  {ROLE_TOKEN_PRODUCER},              target=8),
            ArchetypeBucket("token_doublers",   {ROLE_TOKEN_DOUBLER},               target=2),
            ArchetypeBucket("leaves_bf",        {ROLE_LEAVES_BATTLEFIELD},          target=3),
        ],
        role_boosts={
            ROLE_SACRIFICE_OUTLET:  2.5,
            ROLE_DEATH_TRIGGER:     2.5,
            ROLE_TOKEN_PRODUCER:    2.0,
            ROLE_TOKEN_DOUBLER:     2.5,
            ROLE_LEAVES_BATTLEFIELD: 2.0,
            ROLE_RECURSION:         1.5,
        },
    ),
    ARCH_TOKENS: Archetype(
        name=ARCH_TOKENS,
        extra_buckets=[
            ArchetypeBucket("token_producers",  {ROLE_TOKEN_PRODUCER},              target=8),
            ArchetypeBucket("token_doublers",   {ROLE_TOKEN_DOUBLER},               target=3),
            ArchetypeBucket("sac_outlets",      {ROLE_SACRIFICE_OUTLET},            target=3),
            ArchetypeBucket("death_triggers",   {ROLE_DEATH_TRIGGER},               target=3),
        ],
        role_boosts={
            ROLE_TOKEN_PRODUCER:    2.5,
            ROLE_TOKEN_DOUBLER:     3.0,
            ROLE_SACRIFICE_OUTLET:  1.5,
            ROLE_DEATH_TRIGGER:     1.5,
            ROLE_HASTE_ENABLER:     1.5,
        },
    ),
    ARCH_GRAVEYARD: Archetype(
        name=ARCH_GRAVEYARD,
        extra_buckets=[
            ArchetypeBucket("recursion",        {ROLE_RECURSION},                   target=6),
            ArchetypeBucket("sac_outlets",      {ROLE_SACRIFICE_OUTLET},            target=4),
            ArchetypeBucket("death_triggers",   {ROLE_DEATH_TRIGGER},               target=4),
            ArchetypeBucket("grave_hate",       {ROLE_GRAVEYARD_HATE},              target=2),
        ],
        role_boosts={
            ROLE_RECURSION:         2.5,
            ROLE_SACRIFICE_OUTLET:  2.0,
            ROLE_DEATH_TRIGGER:     2.0,
            ROLE_GRAVEYARD_HATE:    1.5,
        },
    ),
    ARCH_SPELLSLINGER: Archetype(
        name=ARCH_SPELLSLINGER,
        extra_buckets=[
            ArchetypeBucket("counterspells",    {ROLE_COUNTERSPELL},                target=5),
            ArchetypeBucket("cost_reducers",    {ROLE_COST_REDUCER},                target=3),
        ],
        role_boosts={
            ROLE_COUNTERSPELL:  2.0,
            ROLE_COST_REDUCER:  2.0,
            ROLE_CARD_DRAW:     1.5,
        },
    ),
    ARCH_DRAGONS: Archetype(
        name=ARCH_DRAGONS,
        extra_buckets=[
            ArchetypeBucket("cost_reducers",    {ROLE_COST_REDUCER},                target=4),
            ArchetypeBucket("haste_enablers",   {ROLE_HASTE_ENABLER},               target=3),
            ArchetypeBucket("combat_triggers",  {ROLE_COMBAT_TRIGGER},              target=4),
        ],
        role_boosts={
            ROLE_COST_REDUCER:  2.5,
            ROLE_HASTE_ENABLER: 2.0,
            ROLE_COMBAT_TRIGGER: 2.0,
        },
    ),
    ARCH_VOLTRON: Archetype(
        name=ARCH_VOLTRON,
        extra_buckets=[
            ArchetypeBucket("protection",       {ROLE_PROTECTION},                  target=6),
            ArchetypeBucket("extra_combats",    {ROLE_EXTRA_COMBAT},                target=3),
            ArchetypeBucket("combat_triggers",  {ROLE_COMBAT_TRIGGER},              target=4),
        ],
        role_boosts={
            ROLE_PROTECTION:    2.5,
            ROLE_EXTRA_COMBAT:  2.5,
            ROLE_COMBAT_TRIGGER: 2.0,
            ROLE_HASTE_ENABLER: 1.5,
        },
    ),
    ARCH_COMBAT: Archetype(
        name=ARCH_COMBAT,
        extra_buckets=[
            ArchetypeBucket("extra_combats",    {ROLE_EXTRA_COMBAT},                target=4),
            ArchetypeBucket("haste_enablers",   {ROLE_HASTE_ENABLER},               target=3),
            ArchetypeBucket("combat_triggers",  {ROLE_COMBAT_TRIGGER},              target=5),
        ],
        role_boosts={
            ROLE_EXTRA_COMBAT:  2.5,
            ROLE_HASTE_ENABLER: 2.0,
            ROLE_COMBAT_TRIGGER: 2.0,
        },
    ),
    ARCH_COUNTERS: Archetype(
        name=ARCH_COUNTERS,
        extra_buckets=[
            ArchetypeBucket("token_producers",  {ROLE_TOKEN_PRODUCER},              target=4),
            ArchetypeBucket("sac_outlets",      {ROLE_SACRIFICE_OUTLET},            target=3),
        ],
        role_boosts={
            ROLE_TOKEN_PRODUCER: 1.5,
            ROLE_SACRIFICE_OUTLET: 1.5,
        },
    ),
}


# ── Detection patterns ────────────────────────────────────────────────────────

_DETECT: list[tuple[str, str]] = [
    # Sacrifice
    (ARCH_SACRIFICE, r"\bsacrifice\b"),
    (ARCH_SACRIFICE, r"whenever .{0,30}(creature|permanent).{0,20}dies?"),
    (ARCH_SACRIFICE, r"whenever .{0,30}is put into a graveyard from the battlefield"),
    # Tokens
    (ARCH_TOKENS,    r"create .{0,30}token"),
    (ARCH_TOKENS,    r"token.{0,30}(you control|enters? the battlefield)"),
    # Graveyard
    (ARCH_GRAVEYARD, r"(graveyard|from your graveyard|return .{0,30}from .{0,20}graveyard)"),
    (ARCH_GRAVEYARD, r"dredge|delve|escape|flashback|unearth|reanimate"),
    # Spellslinger
    (ARCH_SPELLSLINGER, r"whenever you cast (a |an )(instant|sorcery|spell)"),
    (ARCH_SPELLSLINGER, r"(instant|sorcery) spells? .{0,30}cost"),
    # Dragons
    (ARCH_DRAGONS,   r"\bdragon\b"),
    # Voltron / equip
    (ARCH_VOLTRON,   r"\bequip\b"),
    (ARCH_VOLTRON,   r"\baura\b"),
    (ARCH_VOLTRON,   r"\bvoltron\b"),
    # Combat / aggro
    (ARCH_COMBAT,    r"additional combat phase"),
    (ARCH_COMBAT,    r"whenever .{0,30}attacks?"),
    (ARCH_COMBAT,    r"whenever .{0,30}deals combat damage"),
    # +1/+1 counters
    (ARCH_COUNTERS,  r"\+1/\+1 counter"),
    (ARCH_COUNTERS,  r"proliferate"),
]

# Additional type-line heuristics
_TYPE_HEURISTICS: list[tuple[str, str]] = [
    (ARCH_DRAGONS,    r"\bdragon\b"),
    (ARCH_TRIBAL,     r"\b(elf|elves|goblin|zombie|vampire|merfolk|wizard|warrior|soldier)\b"),
]


def detect_archetypes(oracle_text: str, type_line: str) -> list[str]:
    """Return all detected archetype names for a commander's oracle text + type line."""
    found: set[str] = set()
    combined = (oracle_text or "").lower()

    for arch, pattern in _DETECT:
        if re.search(pattern, combined, re.I):
            found.add(arch)

    # Type-line pass
    tl = (type_line or "").lower()
    for arch, pattern in _TYPE_HEURISTICS:
        if re.search(pattern, tl, re.I):
            found.add(arch)

    return sorted(found)


def get_archetype_objects(archetypes: list[str]) -> list[Archetype]:
    return [_ARCHETYPES[a] for a in archetypes if a in _ARCHETYPES]


def merged_extra_buckets(archetypes: list[Archetype]) -> list[ArchetypeBucket]:
    """Merge extra buckets from multiple archetypes; dedupe by name, keep highest target."""
    seen: dict[str, ArchetypeBucket] = {}
    for arch in archetypes:
        for bucket in arch.extra_buckets:
            if bucket.name not in seen or bucket.target > seen[bucket.name].target:
                seen[bucket.name] = bucket
    return list(seen.values())


def merged_role_boosts(archetypes: list[Archetype]) -> dict[str, float]:
    """Merge role boosts; take the max multiplier for each role."""
    boosts: dict[str, float] = {}
    for arch in archetypes:
        for role, mult in arch.role_boosts.items():
            boosts[role] = max(boosts.get(role, 1.0), mult)
    return boosts
