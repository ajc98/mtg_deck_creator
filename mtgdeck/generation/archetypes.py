"""Archetype detection and dynamic bucket definitions for Commander deckbuilding.

Archetypes add mandatory role buckets on top of the baseline buckets, ensuring
that implicit fuel cards (Scute Swarm for sacrifice, Proliferate for counters,
discard outlets for graveyard, etc.) enter the deck even when EDHREC and vector
search don't surface them because they share no oracle text with the commander.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from mtgdeck.scoring.role_classifier import (
    ROLE_ANTHEM,
    ROLE_BLINK,
    ROLE_BOARD_WIPE,
    ROLE_CARD_DRAW,
    ROLE_CHANGELING,
    ROLE_COMBAT_TRIGGER,
    ROLE_COST_REDUCER,
    ROLE_COUNTER_STORE,
    ROLE_COUNTERSPELL,
    ROLE_DEATH_TRIGGER,
    ROLE_DISCARD_OUTLET,
    ROLE_ETB_PAYOFF,
    ROLE_EVASION_GIVER,
    ROLE_EXTRA_COMBAT,
    ROLE_EXTRA_LAND_DROP,
    ROLE_GRAVEYARD_HATE,
    ROLE_HASTE_ENABLER,
    ROLE_LAND_RAMP,
    ROLE_LEAVES_BATTLEFIELD,
    ROLE_LIFEGAIN,
    ROLE_MANA_DORK,
    ROLE_MANA_ROCK,
    ROLE_OVERRUN,
    ROLE_PROLIFERATE,
    ROLE_PROTECTION,
    ROLE_RECURSION,
    ROLE_REMOVAL,
    ROLE_SACRIFICE_OUTLET,
    ROLE_SELF_MILL,
    ROLE_SPELL_COPY,
    ROLE_TOKEN_DOUBLER,
    ROLE_TOKEN_PRODUCER,
    ROLE_TRIBAL_LORD,
    ROLE_LAND_TYPE_PAYOFF,
    ROLE_SHARED_TYPE,
    ROLE_WHEEL,
    ROLE_WIN_CONDITION,
)

# ── Archetype constants ───────────────────────────────────────────────────────

ARCH_SACRIFICE    = "sacrifice"
ARCH_TOKENS       = "tokens"
ARCH_GRAVEYARD    = "graveyard"
ARCH_SPELLSLINGER = "spellslinger"
ARCH_DRAGONS      = "dragons"
ARCH_VOLTRON      = "voltron"
ARCH_COMBAT       = "combat"
ARCH_COUNTERS     = "counters"
ARCH_TRIBAL       = "tribal"
ARCH_LANDFALL     = "landfall"
ARCH_ETB          = "etb"
ARCH_LIFEGAIN     = "lifegain"
ARCH_ENCHANTRESS  = "enchantress"
ARCH_ARTIFACTS    = "artifacts"
ARCH_CASCADE      = "cascade"
ARCH_ALLTYPE      = "alltype"    # commanders that make creatures every creature type


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
    # role → multiplier applied to sort key in Phase 2 Tier B
    role_boosts: dict[str, float] = field(default_factory=dict)
    # archetypes whose extra_buckets are suppressed when this archetype is detected
    # (e.g. ALLTYPE suppresses COMBAT since attacking is just counter delivery, not strategy)
    suppresses: set[str] = field(default_factory=set)


# ── Archetype definitions ─────────────────────────────────────────────────────

_ARCHETYPES: dict[str, Archetype] = {

    ARCH_SACRIFICE: Archetype(
        name=ARCH_SACRIFICE,
        extra_buckets=[
            ArchetypeBucket("sac_outlets",    {ROLE_SACRIFICE_OUTLET},  target=5),
            ArchetypeBucket("death_triggers",  {ROLE_DEATH_TRIGGER},     target=6),
            ArchetypeBucket("token_producers", {ROLE_TOKEN_PRODUCER},    target=8),
            ArchetypeBucket("token_doublers",  {ROLE_TOKEN_DOUBLER},     target=2),
            ArchetypeBucket("leaves_bf",       {ROLE_LEAVES_BATTLEFIELD},target=3),
        ],
        role_boosts={
            ROLE_SACRIFICE_OUTLET:   2.5,
            ROLE_DEATH_TRIGGER:      2.5,
            ROLE_TOKEN_PRODUCER:     2.0,
            ROLE_TOKEN_DOUBLER:      2.5,
            ROLE_LEAVES_BATTLEFIELD: 2.0,
            ROLE_RECURSION:          1.5,
        },
    ),

    ARCH_TOKENS: Archetype(
        name=ARCH_TOKENS,
        extra_buckets=[
            ArchetypeBucket("token_producers", {ROLE_TOKEN_PRODUCER},    target=8),
            ArchetypeBucket("token_doublers",  {ROLE_TOKEN_DOUBLER},     target=3),
            ArchetypeBucket("overrun",         {ROLE_OVERRUN},           target=3),
            ArchetypeBucket("anthems",         {ROLE_ANTHEM},            target=3),
            ArchetypeBucket("sac_outlets",     {ROLE_SACRIFICE_OUTLET},  target=3),
            ArchetypeBucket("death_triggers",  {ROLE_DEATH_TRIGGER},     target=3),
        ],
        role_boosts={
            ROLE_TOKEN_PRODUCER:  2.5,
            ROLE_TOKEN_DOUBLER:   3.0,
            ROLE_OVERRUN:         2.5,
            ROLE_ANTHEM:          2.0,
            ROLE_SACRIFICE_OUTLET:1.5,
            ROLE_DEATH_TRIGGER:   1.5,
            ROLE_HASTE_ENABLER:   1.5,
        },
    ),

    ARCH_GRAVEYARD: Archetype(
        name=ARCH_GRAVEYARD,
        extra_buckets=[
            ArchetypeBucket("discard_outlets", {ROLE_DISCARD_OUTLET},   target=4),
            ArchetypeBucket("self_mill",        {ROLE_SELF_MILL},        target=4),
            ArchetypeBucket("recursion",        {ROLE_RECURSION},        target=6),
            ArchetypeBucket("sac_outlets",      {ROLE_SACRIFICE_OUTLET}, target=4),
            ArchetypeBucket("death_triggers",   {ROLE_DEATH_TRIGGER},    target=4),
        ],
        role_boosts={
            ROLE_DISCARD_OUTLET: 3.0,
            ROLE_SELF_MILL:      3.0,
            ROLE_RECURSION:      2.5,
            ROLE_SACRIFICE_OUTLET:2.0,
            ROLE_DEATH_TRIGGER:  2.0,
            ROLE_GRAVEYARD_HATE: 1.5,
        },
    ),

    ARCH_SPELLSLINGER: Archetype(
        name=ARCH_SPELLSLINGER,
        extra_buckets=[
            ArchetypeBucket("counterspells",  {ROLE_COUNTERSPELL},   target=5),
            ArchetypeBucket("cost_reducers",  {ROLE_COST_REDUCER},   target=3),
            ArchetypeBucket("wheels",         {ROLE_WHEEL},          target=3),
            ArchetypeBucket("spell_copies",   {ROLE_SPELL_COPY},     target=2),
            ArchetypeBucket("discard_outlets",{ROLE_DISCARD_OUTLET}, target=2),
        ],
        role_boosts={
            ROLE_COUNTERSPELL:    2.0,
            ROLE_COST_REDUCER:    2.0,
            ROLE_WHEEL:           2.5,
            ROLE_SPELL_COPY:      2.5,
            ROLE_DISCARD_OUTLET:  1.5,
            ROLE_CARD_DRAW:       1.5,
        },
    ),

    ARCH_DRAGONS: Archetype(
        name=ARCH_DRAGONS,
        extra_buckets=[
            ArchetypeBucket("cost_reducers",   {ROLE_COST_REDUCER},  target=4),
            ArchetypeBucket("haste_enablers",  {ROLE_HASTE_ENABLER}, target=3),
            ArchetypeBucket("combat_triggers", {ROLE_COMBAT_TRIGGER},target=4),
            ArchetypeBucket("recursion",       {ROLE_RECURSION},     target=3),
        ],
        role_boosts={
            ROLE_COST_REDUCER:   2.5,
            ROLE_HASTE_ENABLER:  2.0,
            ROLE_COMBAT_TRIGGER: 2.0,
            ROLE_RECURSION:      1.5,
        },
    ),

    ARCH_VOLTRON: Archetype(
        name=ARCH_VOLTRON,
        extra_buckets=[
            ArchetypeBucket("protection",     {ROLE_PROTECTION},     target=6),
            ArchetypeBucket("extra_combats",  {ROLE_EXTRA_COMBAT},   target=3),
            ArchetypeBucket("combat_triggers",{ROLE_COMBAT_TRIGGER}, target=4),
            ArchetypeBucket("evasion_givers", {ROLE_EVASION_GIVER},  target=3),
            ArchetypeBucket("anthems",        {ROLE_ANTHEM},         target=2),
        ],
        role_boosts={
            ROLE_PROTECTION:     2.5,
            ROLE_EXTRA_COMBAT:   2.5,
            ROLE_COMBAT_TRIGGER: 2.0,
            ROLE_EVASION_GIVER:  2.0,
            ROLE_ANTHEM:         1.5,
            ROLE_HASTE_ENABLER:  1.5,
        },
    ),

    ARCH_COMBAT: Archetype(
        name=ARCH_COMBAT,
        extra_buckets=[
            ArchetypeBucket("extra_combats",  {ROLE_EXTRA_COMBAT},   target=4),
            ArchetypeBucket("haste_enablers", {ROLE_HASTE_ENABLER},  target=3),
            ArchetypeBucket("combat_triggers",{ROLE_COMBAT_TRIGGER}, target=5),
            ArchetypeBucket("evasion_givers", {ROLE_EVASION_GIVER},  target=3),
        ],
        role_boosts={
            ROLE_EXTRA_COMBAT:   2.5,
            ROLE_HASTE_ENABLER:  2.0,
            ROLE_COMBAT_TRIGGER: 2.0,
            ROLE_EVASION_GIVER:  1.8,
        },
    ),

    ARCH_COUNTERS: Archetype(
        name=ARCH_COUNTERS,
        extra_buckets=[
            ArchetypeBucket("proliferate",    {ROLE_PROLIFERATE},    target=5),
            ArchetypeBucket("token_producers",{ROLE_TOKEN_PRODUCER}, target=4),
            ArchetypeBucket("sac_outlets",    {ROLE_SACRIFICE_OUTLET},target=3),
        ],
        role_boosts={
            ROLE_PROLIFERATE:    3.0,
            ROLE_TOKEN_PRODUCER: 1.5,
            ROLE_TOKEN_DOUBLER:  2.0,
            ROLE_SACRIFICE_OUTLET:1.5,
        },
    ),

    ARCH_TRIBAL: Archetype(
        name=ARCH_TRIBAL,
        extra_buckets=[
            ArchetypeBucket("changelings",    {ROLE_CHANGELING},     target=3),
            ArchetypeBucket("anthems",        {ROLE_ANTHEM},         target=3),
        ],
        role_boosts={
            ROLE_CHANGELING: 3.0,
            ROLE_ANTHEM:     2.0,
        },
    ),

    ARCH_LANDFALL: Archetype(
        name=ARCH_LANDFALL,
        extra_buckets=[
            ArchetypeBucket("extra_land_drops",{ROLE_EXTRA_LAND_DROP},target=4),
            ArchetypeBucket("token_producers", {ROLE_TOKEN_PRODUCER}, target=5),
            ArchetypeBucket("overrun",         {ROLE_OVERRUN},        target=2),
        ],
        role_boosts={
            ROLE_EXTRA_LAND_DROP: 3.0,
            ROLE_LAND_RAMP:       1.5,
            ROLE_TOKEN_PRODUCER:  2.0,
            ROLE_OVERRUN:         2.0,
            ROLE_RECURSION:       1.5,  # land recursion (Crucible, Life from the Loam)
        },
    ),

    ARCH_ETB: Archetype(
        name=ARCH_ETB,
        extra_buckets=[
            ArchetypeBucket("blink",          {ROLE_BLINK},          target=4),
            ArchetypeBucket("etb_payoffs",    {ROLE_ETB_PAYOFF},     target=4),
            ArchetypeBucket("token_doublers", {ROLE_TOKEN_DOUBLER},  target=2),
        ],
        role_boosts={
            ROLE_BLINK:       3.0,
            ROLE_ETB_PAYOFF:  3.0,
            ROLE_TOKEN_DOUBLER:2.0,
        },
    ),

    ARCH_LIFEGAIN: Archetype(
        name=ARCH_LIFEGAIN,
        extra_buckets=[
            ArchetypeBucket("lifegain_payoffs",{ROLE_WIN_CONDITION},  target=4),
            ArchetypeBucket("token_producers", {ROLE_TOKEN_PRODUCER}, target=4),
            ArchetypeBucket("anthems",         {ROLE_ANTHEM},         target=2),
        ],
        role_boosts={
            ROLE_WIN_CONDITION:  2.5,
            ROLE_LIFEGAIN:       2.0,
            ROLE_TOKEN_PRODUCER: 1.5,
        },
    ),

    ARCH_ENCHANTRESS: Archetype(
        name=ARCH_ENCHANTRESS,
        extra_buckets=[
            ArchetypeBucket("card_draw",      {ROLE_CARD_DRAW},      target=6),
            ArchetypeBucket("protection",     {ROLE_PROTECTION},     target=4),
            ArchetypeBucket("anthems",        {ROLE_ANTHEM},         target=3),
        ],
        role_boosts={
            ROLE_CARD_DRAW:  2.0,
            ROLE_PROTECTION: 1.8,
            ROLE_ANTHEM:     1.8,
        },
    ),

    ARCH_ARTIFACTS: Archetype(
        name=ARCH_ARTIFACTS,
        extra_buckets=[
            ArchetypeBucket("etb_payoffs",    {ROLE_ETB_PAYOFF},     target=4),
            ArchetypeBucket("token_doublers", {ROLE_TOKEN_DOUBLER},  target=2),
            ArchetypeBucket("recursion",      {ROLE_RECURSION},      target=3),
            ArchetypeBucket("token_producers",{ROLE_TOKEN_PRODUCER}, target=4),
        ],
        role_boosts={
            ROLE_ETB_PAYOFF:  3.0,
            ROLE_TOKEN_DOUBLER:2.5,
            ROLE_RECURSION:   2.0,
            ROLE_TOKEN_PRODUCER:1.8,
        },
    ),

    # "Every creature type" commanders (Omo, Morophon, etc.)
    # When creatures become every creature type, ALL tribal lords become global anthems.
    # The deck needs lords from every tribe — their "other [Type] get +1/+1" effect
    # applies to your whole board. Counter support (Ozolith, Goldberry) preserves the
    # everything counters when creatures die. Haste/blink lets you re-trigger the
    # placement effect to give every creature the buff quickly.
    # Suppresses COMBAT because the "attack" trigger is counter delivery, not strategy —
    # combat buckets (extra combats, evasion givers) waste archetype slots.
    ARCH_ALLTYPE: Archetype(
        name=ARCH_ALLTYPE,
        extra_buckets=[
            ArchetypeBucket("tribal_lords",      {ROLE_TRIBAL_LORD},      target=8),
            ArchetypeBucket("counter_stores",    {ROLE_COUNTER_STORE},    target=4),
            ArchetypeBucket("shared_type",       {ROLE_SHARED_TYPE},      target=2),
            ArchetypeBucket("haste_enablers",    {ROLE_HASTE_ENABLER},    target=3),
            ArchetypeBucket("blink",             {ROLE_BLINK},            target=3),
            ArchetypeBucket("anthems",           {ROLE_ANTHEM},           target=3),
            ArchetypeBucket("changelings",       {ROLE_CHANGELING},       target=3),
            ArchetypeBucket("land_type_payoffs", {ROLE_LAND_TYPE_PAYOFF}, target=3),
        ],
        role_boosts={
            ROLE_TRIBAL_LORD:     4.0,   # highest priority — lords are the win condition
            ROLE_COUNTER_STORE:   3.5,   # Ozolith/Goldberry are critical support
            ROLE_SHARED_TYPE:     3.5,   # Coat of Arms is game-ending with every creature type
            ROLE_HASTE_ENABLER:   2.5,   # need to trigger Omo's attack ability immediately
            ROLE_BLINK:           2.5,   # re-trigger ETB to spread more counters
            ROLE_ANTHEM:          2.0,
            ROLE_CHANGELING:      2.0,
            ROLE_PROLIFERATE:     1.8,   # spread counters further
            ROLE_LAND_TYPE_PAYOFF:1.5,   # Desert/Gate subtheme payoffs
        },
        # COUNTERS is also suppressed: ALLTYPE's own counter_stores bucket already covers
        # Ozolith/Goldberry. COUNTERS' proliferate/sac_outlets waste Omo's limited arch slots.
        suppresses={ARCH_COMBAT, ARCH_COUNTERS},
    ),

    # Cascade commanders (Abaddon, Yidris, etc.) need high-CMC spells to cascade
    # into, mass-draw to find threats, and ways to repeatedly trigger the mechanic.
    # They also benefit from protection to keep the commander alive long enough
    # to cascade multiple times.
    ARCH_CASCADE: Archetype(
        name=ARCH_CASCADE,
        extra_buckets=[
            ArchetypeBucket("win_conditions",  {ROLE_WIN_CONDITION},  target=5),
            ArchetypeBucket("card_draw",       {ROLE_CARD_DRAW},      target=5),
            ArchetypeBucket("haste_enablers",  {ROLE_HASTE_ENABLER},  target=3),
            ArchetypeBucket("protection",      {ROLE_PROTECTION},     target=4),
            ArchetypeBucket("combat_triggers", {ROLE_COMBAT_TRIGGER}, target=4),
        ],
        role_boosts={
            ROLE_WIN_CONDITION:  2.5,
            ROLE_CARD_DRAW:      2.0,
            ROLE_HASTE_ENABLER:  2.5,
            ROLE_PROTECTION:     2.0,
            ROLE_COMBAT_TRIGGER: 2.0,
        },
    ),
}


# ── Detection patterns ────────────────────────────────────────────────────────

_DETECT: list[tuple[str, str]] = [
    # Tokens — four patterns to catch creators, doublers, and payoffs
    # Pattern 1: short creation ("create X token") — also see long-type pattern at bottom
    (ARCH_TOKENS,    r"create .{0,30}token"),
    # Pattern 2: commander cares about tokens you control — catches both
    # "you control" and "under your control" phrasing (Adrix-style doublers)
    (ARCH_TOKENS,    r"token.{0,40}(you(r)? control|enters? the battlefield)"),
    # Pattern 3: commander doubles or modifies token creation
    (ARCH_TOKENS,    r"(twice as many|additional|double).{0,30}token"),
    # Pattern 4: triggered off tokens (payoff commanders)
    (ARCH_TOKENS,    r"whenever .{0,20}(token|tokens).{0,20}(enters?|created|dies?)"),
    # Graveyard
    (ARCH_GRAVEYARD, r"\bgraveyard\b"),
    (ARCH_GRAVEYARD, r"from (your|a) graveyard"),
    (ARCH_GRAVEYARD, r"dredge|delve|escape|flashback|unearth|reanimate"),
    (ARCH_GRAVEYARD, r"put .{0,30}into (your|a) graveyard"),
    # Spellslinger
    (ARCH_SPELLSLINGER, r"whenever you cast (a |an )(instant|sorcery|spell)"),
    (ARCH_SPELLSLINGER, r"(instant|sorcery) spells?.{0,30}cost"),
    (ARCH_SPELLSLINGER, r"magecraft"),
    # Dragons
    (ARCH_DRAGONS,   r"\bdragon\b"),
    # Voltron / equip
    (ARCH_VOLTRON,   r"\bequip\b"),
    (ARCH_VOLTRON,   r"\baura\b"),
    # Combat / aggro — allow up to 45 chars between 'whenever' and 'attacks'
    # so "whenever two or more creatures you control attack" is caught
    (ARCH_COMBAT,    r"additional combat phase"),
    (ARCH_COMBAT,    r"whenever .{0,45}attacks?"),
    (ARCH_COMBAT,    r"whenever .{0,30}deals combat damage"),
    # +1/+1 counters — also catch generic "counter" strategies (shield, charge, etc.)
    (ARCH_COUNTERS,  r"\+1/\+1 counter"),
    (ARCH_COUNTERS,  r"proliferate"),
    (ARCH_COUNTERS,  r"removing a counter from"),   # Falco Spara, Ozolith-style commanders
    (ARCH_COUNTERS,  r"move .{0,20}counter"),        # Goldberry, counter-moving commanders
    # Every-creature-type commanders (Omo, Morophon) — tribal lords become global anthems
    (ARCH_ALLTYPE,   r"every creature type"),
    (ARCH_ALLTYPE,   r"each creature type"),
    (ARCH_ALLTYPE,   r"all creature types"),
    (ARCH_ALLTYPE,   r"is every (land|creature) type"),
    # Also catch: general counter placement (Omo's "put an everything counter on")
    # These commanders need counter support (Ozolith, Goldberry, proliferate)
    (ARCH_COUNTERS,  r"put (a |an )?\w+ counter on (target|each|up to)"),
    # Cascade — commander gives cascade to spells; needs draw + high-CMC threats
    (ARCH_CASCADE,   r"\bcascade\b"),
    # Tribal — detected from type line heuristics below
    # Landfall — also catch commanders that grant extra land drops (they NEED landfall fuel)
    (ARCH_LANDFALL,  r"landfall"),
    (ARCH_LANDFALL,  r"whenever .{0,20}land .{0,20}enters"),
    (ARCH_LANDFALL,  r"whenever a land (you control )?(enters|enters the battlefield)"),
    (ARCH_LANDFALL,  r"you may play (an? additional|\d+ additional) land"),
    # ETB value commanders — fixed to catch "whenever another X you control enters"
    # by allowing optional qualifier between the type word and 'enters'
    (ARCH_ETB,       r"when(ever)? .{0,30}(enters|enters the battlefield).{0,40}you control"),
    (ARCH_ETB,       r"when(ever)? (this|another) (creature|artifact|permanent|legendary).{0,25}enters"),
    (ARCH_ETB,       r"whenever another (creature|artifact|permanent).{0,25}enters"),
    # Lifegain — both commanders that generate lifegain AND commanders that spend
    # life as a resource (Asmodeus, K'rrik, Bolas's Citadel users), since those
    # commanders need lifegain fuel just as badly as payoff commanders do.
    # Also catch variable "gain X life" (not just fixed digits).
    (ARCH_LIFEGAIN,  r"(you )?gains? (\d+|x) life"),   # fixed and variable amounts
    (ARCH_LIFEGAIN,  r"whenever (you |a player )?gains? life"),
    (ARCH_LIFEGAIN,  r"life total"),
    (ARCH_LIFEGAIN,  r"pay .{0,15}life"),               # any life payment (fixed or variable)
    (ARCH_LIFEGAIN,  r"you lose .{0,15}life"),          # variable life cost (Asmodeus, etc.)
    (ARCH_LIFEGAIN,  r"phyrexian mana|\{[WUBRG]/P\}"),  # Phyrexian mana = life payment
    (ARCH_LIFEGAIN,  r"lifelink"),                      # built-in lifelink → generates life
    # Enchantress
    (ARCH_ENCHANTRESS, r"whenever (you cast|an?) enchantment"),
    (ARCH_ENCHANTRESS, r"enchantment (spells?|cards?).{0,30}you cast"),
    (ARCH_ENCHANTRESS, r"constellation"),
    # Artifacts — including artifact lord commanders (buff artifact creatures)
    (ARCH_ARTIFACTS, r"whenever (you cast|an?) artifact"),
    (ARCH_ARTIFACTS, r"artifact (spells?|cards?).{0,30}you cast"),
    (ARCH_ARTIFACTS, r"whenever an? artifact (enters|enters the battlefield)"),
    (ARCH_ARTIFACTS, r"(other )?artifact creatures you control"),  # lords like Krang
    (ARCH_ARTIFACTS, r"whenever you activate.{0,30}artifact"),     # Kurkesh-style
    # Sacrifice — also catch 'sacrificed' (past tense) for cost-reduction commanders
    (ARCH_SACRIFICE, r"\bsacrific"),                               # sacrifice/sacrificed/sacrificing
    (ARCH_SACRIFICE, r"whenever .{0,30}(creature|permanent).{0,20}dies?"),
    (ARCH_SACRIFICE, r"whenever .{0,30}is put into a graveyard from the battlefield"),
    # Token creation with long type lines (e.g. "1/1 green Forest Dryad land creature token")
    # Extend from 30 to 50 chars to catch these verbose descriptions
    (ARCH_TOKENS,    r"create .{0,50}token"),
    # ETB: catch "When [Name] enters" — self-referential ETB trigger by proper name
    # (Gonti, Sauron, Lizard-type commanders that trigger on own entry)
    # Pattern: sentence starts with "When" followed by a capitalized word (not a generic
    # determiner like 'a', 'an', 'another', 'this', 'the', 'each', 'you')
    (ARCH_ETB,       r"when (?!a |an |another |this |the |each |you )[A-Z]\w.{0,50}enters"),
    # Combat: menace and sneak-attack commanders are fundamentally aggressive
    # and need the same fuel as other combat commanders (haste, protection, evasion)
    (ARCH_COMBAT,    r"\bmenace\b"),
    (ARCH_COMBAT,    r"can't be blocked by more than one"),  # Rocksteady-style pseudo-menace
    (ARCH_COMBAT,    r"\bsneak \{"),          # Sneak {X} — attack-from-hand mechanic
    (ARCH_COMBAT,    r"each opponent.{0,30}(dealt combat damage|takes damage)"),
    # Artifacts: commanders that use artifacts as alternative cost or resource
    (ARCH_ARTIFACTS, r"tap (an? |an? untapped )?artifact you control"),
    # Spellslinger: grandeur and similar "discard to tutor spells" effects
    (ARCH_SPELLSLINGER, r"grandeur"),
    (ARCH_SPELLSLINGER, r"discard .{0,30}(instant|sorcery)"),
    # Graveyard: draw-then-discard loop commanders (Troyan, Kefnet-style)
    # and hand-size-matters commanders that bounce lands for reuse
    (ARCH_GRAVEYARD, r"draw a card.{0,40}discard"),
    (ARCH_GRAVEYARD, r"discard.{0,40}draw a card"),
]

# Type-line heuristics (applied to commander type_line)
_TYPE_HEURISTICS: list[tuple[str, str]] = [
    (ARCH_DRAGONS,   r"\bdragon\b"),
    (ARCH_TRIBAL,    r"\b(angel|angels|elf|elves|goblin|goblins|zombie|zombies|"
                     r"vampire|vampires|merfolk|wizard|wizards|warrior|warriors|"
                     r"soldier|soldiers|human|humans|knight|knights|pirate|pirates|"
                     r"cat|cats|shaman|shamans|cleric|clerics|druid|druids|"
                     r"bird|birds|dinosaur|dinosaurs|faerie|faeries|treefolk|"
                     r"beast|beasts|elemental|elementals|spirit|spirits|"
                     r"sliver|slivers|bear|bears|insect|insects|snake|snakes|"
                     r"dwarf|dwarves|giant|giants|demon|demons|angel|angels)\b"),
]


def detect_archetypes(oracle_text: str, type_line: str) -> list[str]:
    """Return all detected archetype names for a commander's oracle text + type line."""
    found: set[str] = set()
    combined = (oracle_text or "").lower()

    for arch, pattern in _DETECT:
        if re.search(pattern, combined, re.I):
            found.add(arch)

    tl = (type_line or "").lower()
    for arch, pattern in _TYPE_HEURISTICS:
        if re.search(pattern, tl, re.I):
            found.add(arch)

    return sorted(found)


def get_archetype_objects(archetypes: list[str]) -> list[Archetype]:
    return [_ARCHETYPES[a] for a in archetypes if a in _ARCHETYPES]


def merged_extra_buckets(archetypes: list[Archetype]) -> list[ArchetypeBucket]:
    """Merge extra buckets; dedupe by name, keep highest target.

    If any archetype lists another in its `suppresses` set, that other archetype's
    extra_buckets are excluded — its role_boosts still apply for scoring, but it
    won't claim mandatory slots (e.g. ALLTYPE suppresses COMBAT so attack-phase
    buckets don't compete with tribal lord and counter store slots).
    """
    suppressed: set[str] = set()
    for arch in archetypes:
        suppressed.update(arch.suppresses)

    seen: dict[str, ArchetypeBucket] = {}
    for arch in archetypes:
        if arch.name in suppressed:
            continue
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
