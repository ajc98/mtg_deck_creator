"""Oracle-text pattern-based card role classifier."""
from __future__ import annotations

import re

from mtgdeck.models import BASIC_LAND_NAMES

# ── Role string constants ────────────────────────────────────────────────────
ROLE_BASIC_LAND         = "basic_land"
ROLE_LAND               = "land"
ROLE_MANA_ROCK          = "mana_rock"
ROLE_MANA_DORK          = "mana_dork"
ROLE_LAND_RAMP          = "land_ramp"
ROLE_CARD_DRAW          = "card_draw"
ROLE_TUTOR              = "tutor"
ROLE_REMOVAL            = "removal"
ROLE_BOARD_WIPE         = "board_wipe"
ROLE_COUNTERSPELL       = "counterspell"
ROLE_PROTECTION         = "protection"
ROLE_RECURSION          = "recursion"
ROLE_GRAVEYARD_HATE     = "graveyard_hate"
ROLE_SACRIFICE_OUTLET   = "sacrifice_outlet"
ROLE_DEATH_TRIGGER      = "death_trigger"       # fires when creatures die
ROLE_TOKEN_PRODUCER     = "token_producer"
ROLE_TOKEN_DOUBLER      = "token_doubler"        # doubles/multiplies token creation
ROLE_LEAVES_BATTLEFIELD = "leaves_battlefield"   # triggers when permanents leave
ROLE_EXTRA_COMBAT       = "extra_combat"         # additional attack steps
ROLE_HASTE_ENABLER      = "haste_enabler"        # grants haste to others
ROLE_COST_REDUCER       = "cost_reducer"         # reduces spell/creature costs
ROLE_COMBAT_TRIGGER     = "combat_trigger"       # triggers on attack or combat damage
ROLE_LIFEGAIN           = "lifegain"
ROLE_WIN_CONDITION      = "win_condition"
ROLE_SYNERGY            = "synergy"

# ── New implicit-fuel roles ──────────────────────────────────────────────────
ROLE_DISCARD_OUTLET     = "discard_outlet"    # voluntary self-discard (Faithless Looting)
ROLE_SELF_MILL          = "self_mill"         # put own cards into graveyard
ROLE_PROLIFERATE        = "proliferate"       # proliferate keyword
ROLE_OVERRUN            = "overrun"           # give all creatures +N/+N and trample
ROLE_EVASION_GIVER      = "evasion_giver"     # grant mass flying/trample/unblockable
ROLE_EXTRA_LAND_DROP    = "extra_land_drop"   # play additional land(s) per turn
ROLE_BLINK              = "blink"             # exile and return own permanents
ROLE_ANTHEM             = "anthem"            # give all creatures +N/+N permanently
ROLE_CHANGELING         = "changeling"        # every creature type
ROLE_WHEEL              = "wheel"             # everyone draws/discards and redraws
ROLE_ETB_PAYOFF         = "etb_payoff"        # triggers when creatures enter (Purphoros)
ROLE_SPELL_COPY         = "spell_copy"        # copy instants/sorceries (Fork, Reverberate)
ROLE_TRIBAL_LORD        = "tribal_lord"       # buffs all creatures of a specific type ("other Elves get +1/+1")
ROLE_COUNTER_STORE      = "counter_store"     # preserves or moves counters (Ozolith, Goldberry)
ROLE_SHARED_TYPE        = "shared_type"       # scales with shared creature types (Coat of Arms)
ROLE_LAND_TYPE_PAYOFF   = "land_type_payoff"  # triggers/scales when controlling many of a land type

# Sets for bucket membership checks
RAMP_ROLES        = {ROLE_MANA_ROCK, ROLE_MANA_DORK, ROLE_LAND_RAMP}
DRAW_ROLES        = {ROLE_CARD_DRAW, ROLE_TUTOR}
INTERACTION_ROLES = {ROLE_REMOVAL, ROLE_BOARD_WIPE, ROLE_COUNTERSPELL}
LAND_ROLES        = {ROLE_LAND, ROLE_BASIC_LAND}

# Human-readable labels
ROLE_LABELS: dict[str, str] = {
    ROLE_BASIC_LAND:         "Basic Land",
    ROLE_LAND:               "Land",
    ROLE_MANA_ROCK:          "Mana Rock",
    ROLE_MANA_DORK:          "Mana Dork",
    ROLE_LAND_RAMP:          "Land Ramp",
    ROLE_CARD_DRAW:          "Card Draw",
    ROLE_TUTOR:              "Tutor",
    ROLE_REMOVAL:            "Removal",
    ROLE_BOARD_WIPE:         "Board Wipe",
    ROLE_COUNTERSPELL:       "Counterspell",
    ROLE_PROTECTION:         "Protection",
    ROLE_RECURSION:          "Recursion",
    ROLE_GRAVEYARD_HATE:     "Graveyard Hate",
    ROLE_SACRIFICE_OUTLET:   "Sacrifice Outlet",
    ROLE_DEATH_TRIGGER:      "Death Trigger",
    ROLE_TOKEN_PRODUCER:     "Token Producer",
    ROLE_TOKEN_DOUBLER:      "Token Doubler",
    ROLE_LEAVES_BATTLEFIELD: "Leaves Battlefield",
    ROLE_EXTRA_COMBAT:       "Extra Combat",
    ROLE_HASTE_ENABLER:      "Haste Enabler",
    ROLE_COST_REDUCER:       "Cost Reducer",
    ROLE_COMBAT_TRIGGER:     "Combat Trigger",
    ROLE_LIFEGAIN:           "Lifegain",
    ROLE_WIN_CONDITION:      "Win Condition",
    ROLE_SYNERGY:            "Synergy",
    # implicit-fuel roles
    ROLE_DISCARD_OUTLET:     "Discard Outlet",
    ROLE_SELF_MILL:          "Self-Mill",
    ROLE_PROLIFERATE:        "Proliferate",
    ROLE_OVERRUN:            "Overrun",
    ROLE_EVASION_GIVER:      "Evasion Giver",
    ROLE_EXTRA_LAND_DROP:    "Extra Land Drop",
    ROLE_BLINK:              "Blink",
    ROLE_ANTHEM:             "Anthem",
    ROLE_CHANGELING:         "Changeling",
    ROLE_WHEEL:              "Wheel",
    ROLE_ETB_PAYOFF:         "ETB Payoff",
    ROLE_SPELL_COPY:         "Spell Copy",
    ROLE_TRIBAL_LORD:        "Tribal Lord",
    ROLE_COUNTER_STORE:      "Counter Store",
    ROLE_SHARED_TYPE:        "Shared Type",
    ROLE_LAND_TYPE_PAYOFF:   "Land Type Payoff",
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

    # Death triggers
    (ROLE_DEATH_TRIGGER, r"whenever (a |another |one or more )?(creature|permanent).{0,30}dies?,", re.I),
    (ROLE_DEATH_TRIGGER, r"whenever .{0,30}is put into a graveyard from the battlefield", re.I),
    (ROLE_DEATH_TRIGGER, r"whenever .{0,20}creature (you control |an opponent controls |)dies?", re.I),

    # Token doublers
    (ROLE_TOKEN_DOUBLER, r"(twice as many|creates? .{0,10}additional|double the number).{0,50}token", re.I),
    (ROLE_TOKEN_DOUBLER, r"if .{0,30}would (create|put) (a |an |\d+ )?.{0,20}token", re.I),

    # Leaves-battlefield triggers
    (ROLE_LEAVES_BATTLEFIELD, r"whenever .{0,30}(permanent|creature|artifact|enchantment|land).{0,20}leaves? the battlefield", re.I),
    (ROLE_LEAVES_BATTLEFIELD, r"whenever .{0,30}is put into a graveyard from (the battlefield|play)", re.I),

    # Extra combat steps
    (ROLE_EXTRA_COMBAT, r"additional combat phase", re.I),
    (ROLE_EXTRA_COMBAT, r"(take|gets?) an? extra (combat|attack)", re.I),
    (ROLE_EXTRA_COMBAT, r"untap all (creatures|attacking creatures).{0,40}additional combat", re.I),

    # Haste enablers
    (ROLE_HASTE_ENABLER, r"(creatures? you control|each creature|other creatures?).{0,40}\bhaste\b", re.I),
    (ROLE_HASTE_ENABLER, r"(each|all|other) .{0,20}creatures?.{0,30}(have|gain|gains) haste", re.I),

    # Cost reducers
    (ROLE_COST_REDUCER, r"(dragon|creature|artifact|instant|sorcery).{0,30}(spells?|cards?).{0,30}cost.{0,20}less", re.I),
    (ROLE_COST_REDUCER, r"reduce (the |that )?cost.{0,40}(spell|mana)", re.I),
    (ROLE_COST_REDUCER, r"(spells?|creatures?|artifacts?).{0,20}you cast.{0,20}cost.{0,20}(less|\{[0-9]\})", re.I),

    # Combat/attack triggers
    (ROLE_COMBAT_TRIGGER, r"whenever .{0,30}attacks?,", re.I),
    (ROLE_COMBAT_TRIGGER, r"whenever .{0,30}deals combat damage to (a player|an opponent|a planeswalker)", re.I),

    # ── Implicit fuel roles ──────────────────────────────────────────────────

    # Discard outlet — voluntary self-discard to fill graveyard or loot
    (ROLE_DISCARD_OUTLET, r"draw .{0,20}discard|discard .{0,20}draw", re.I),
    (ROLE_DISCARD_OUTLET, r"you may discard", re.I),
    (ROLE_DISCARD_OUTLET, r"discard (a|a creature|any number of) cards?, (then )?draw", re.I),
    (ROLE_DISCARD_OUTLET, r"\{t\}.{0,40}discard.{0,30}(draw|search)", re.I),
    (ROLE_DISCARD_OUTLET, r"discard (a|a creature) card: (search|draw|look)", re.I),

    # Self-mill — put own cards from library into graveyard
    (ROLE_SELF_MILL, r"\bmills?\b .{0,30}cards?", re.I),
    (ROLE_SELF_MILL, r"\bmills?\b \d+", re.I),
    (ROLE_SELF_MILL, r"\bmills? half", re.I),
    (ROLE_SELF_MILL, r"put the top .{0,30}(card|cards) of (your|their) library into (your|their|a) graveyard", re.I),
    (ROLE_SELF_MILL, r"(controller|player) puts? the top .{0,30}into (a|their|your) graveyard", re.I),
    (ROLE_SELF_MILL, r"reveal the top .{0,60}put .{0,60}into (a|your|their) graveyard", re.I),
    (ROLE_SELF_MILL, r"put the rest into (a|your|their) graveyard", re.I),
    (ROLE_SELF_MILL, r"\bdredge \d+\b", re.I),

    # Proliferate
    (ROLE_PROLIFERATE, r"\bproliferate\b", re.I),

    # Overrun — give all creatures a large buff and trample
    (ROLE_OVERRUN, r"creatures you control (get \+|gain trample)", re.I),
    (ROLE_OVERRUN, r"(each|all) creatures you control .{0,30}trample", re.I),
    (ROLE_OVERRUN, r"creatures you control .{0,30}get \+\d/\+\d", re.I),
    (ROLE_OVERRUN, r"(until end of turn,? )?creatures you control have trample", re.I),

    # Evasion giver — grant mass evasion to your team
    (ROLE_EVASION_GIVER, r"creatures you control (have|gain|gains?).{0,30}(flying|trample|unblockable|can't be blocked)", re.I),
    (ROLE_EVASION_GIVER, r"(all|each) .{0,20}creatures?.{0,30}you control.{0,30}(fly|flying|trample|unblockable)", re.I),
    (ROLE_EVASION_GIVER, r"each creature you control has (flying|trample|unblockable)", re.I),

    # Extra land drop
    (ROLE_EXTRA_LAND_DROP, r"you may play (an? additional|two additional|one additional|\d+ additional) lands? (on each of your turns|this turn|each turn)", re.I),
    (ROLE_EXTRA_LAND_DROP, r"play (up to \d+ additional|an? additional) lands?", re.I),
    (ROLE_EXTRA_LAND_DROP, r"you may play two lands (each turn|on each of your turns)", re.I),

    # Blink — exile and return own permanents to re-trigger ETB
    (ROLE_BLINK, r"exile (target .{0,40}you control|up to \w+ .{0,40}you control).{0,80}return.{0,60}(under your control|battlefield)", re.I),
    (ROLE_BLINK, r"exile (target|up to \w+) .{0,40}(creature|permanent|artifact).{0,60}return.{0,40}under", re.I),

    # Anthem — permanent buff to all your creatures
    (ROLE_ANTHEM, r"creatures you control get \+\d/\+\d", re.I),
    (ROLE_ANTHEM, r"creature tokens you control get \+", re.I),
    (ROLE_ANTHEM, r"other creatures you control get \+", re.I),
    (ROLE_ANTHEM, r"(elves|goblins|zombies|vampires|wizards|warriors|soldiers|merfolk|dragons) .{0,20}you control get \+", re.I),

    # Changeling
    (ROLE_CHANGELING, r"\bchangeling\b", re.I),

    # Wheel — everyone discards hand and redraws
    (ROLE_WHEEL, r"each player discards .{0,30}(hand|cards)", re.I),
    (ROLE_WHEEL, r"each player draws .{0,20}cards", re.I),
    (ROLE_WHEEL, r"(discard your hand|discard their hands).{0,50}draw", re.I),

    # ETB payoff — triggers when YOUR creatures enter (Impact Tremors, Purphoros, Panharmonicon)
    (ROLE_ETB_PAYOFF, r"whenever (a|another|one or more) (creature|artifact|permanent).{0,30}(enters|enters the battlefield) under your control", re.I),
    (ROLE_ETB_PAYOFF, r"whenever a creature (you control )?(enters|enters the battlefield)", re.I),
    (ROLE_ETB_PAYOFF, r"if (a|an|another) (artifact|creature).{0,30}entering.{0,40}triggers?.{0,30}triggers? an additional time", re.I),

    # Spell copy — Fork/Reverberate style
    (ROLE_SPELL_COPY, r"copy (target |an? )?(instant|sorcery|spell)", re.I),

    # Tribal lord — buffs all creatures of a specific type
    # Matches "other Elves/Snakes/Wizards/etc. you control get/gain/have"
    # Key distinction from ANTHEM: there is a specific creature type NAME between
    # "other" and "creatures/you control" (not just "other creatures get")
    (ROLE_TRIBAL_LORD, r"other \w+ (creatures? you control|you control).{0,60}(get \+|\bgain\b|\bhave\b)", re.I),
    (ROLE_TRIBAL_LORD, r"other \w+ creatures?.{0,60}(get \+\d|\bgain\b|\bhave\b)", re.I),
    # Adaptive Automaton, Maskwood Nexus style — "of the chosen type"
    (ROLE_TRIBAL_LORD, r"other (creatures? (of|you control).{0,30}(chosen|named) type|creatures? of that type).{0,40}(get \+|\bgain\b|\bhave\b)", re.I),

    # Counter store/move — Ozolith, Goldberry, counter-transfer effects
    # These are critical fuel for counter-strategy commanders (Omo, Atraxa, etc.)
    (ROLE_COUNTER_STORE, r"put those counters on", re.I),
    (ROLE_COUNTER_STORE, r"move (all |a |one or more )?counters?.{0,30}(from|onto) (target|another)", re.I),
    (ROLE_COUNTER_STORE, r"counters? from .{0,30}onto target", re.I),
    (ROLE_COUNTER_STORE, r"whenever .{0,30}leaves? the battlefield.{0,60}counters? (on it|it had)", re.I),

    # Shared type — scales with how many creatures share a creature type (Coat of Arms)
    # Critical for "every creature type" commanders: all creatures share ALL types → massive buff
    (ROLE_SHARED_TYPE, r"shares? (at least one|a|one) creature type", re.I),
    (ROLE_SHARED_TYPE, r"for each (other )?creature.{0,40}(shares?|of the same) (creature )?type", re.I),
    (ROLE_SHARED_TYPE, r"each creature (of the same type|that shares).{0,40}gets?", re.I),

    # Land type payoff — triggers or scales with controlling lands of a specific named type
    # Covers Desert payoffs (Hashep Oasis subtheme), Gate payoffs, etc.
    (ROLE_LAND_TYPE_PAYOFF, r"for each (desert|gate)s?\b.{0,40}(you control|on the battlefield)", re.I),
    (ROLE_LAND_TYPE_PAYOFF, r"\w+ or more (desert|gate)s?\b", re.I),
    (ROLE_LAND_TYPE_PAYOFF, r"(number of|each) (desert|gate)s? you control", re.I),
    (ROLE_LAND_TYPE_PAYOFF, r"for each land (you control )?that (is|has).{0,20}(desert|gate)\b", re.I),

    (ROLE_SPELL_COPY, r"copies? of (target |that )?(spell|instant|sorcery)", re.I),
    (ROLE_SPELL_COPY, r"you may cast a copy of", re.I),
]

# Priority order for primary role selection (first match wins)
_PRIORITY: list[str] = [
    ROLE_BASIC_LAND,
    ROLE_LAND,
    ROLE_MANA_ROCK,
    ROLE_MANA_DORK,
    ROLE_LAND_RAMP,
    ROLE_EXTRA_LAND_DROP,
    ROLE_TUTOR,
    ROLE_BOARD_WIPE,
    ROLE_COUNTERSPELL,
    ROLE_RECURSION,
    ROLE_REMOVAL,
    ROLE_CARD_DRAW,
    ROLE_DISCARD_OUTLET,
    ROLE_SELF_MILL,
    ROLE_WHEEL,
    ROLE_PROLIFERATE,
    ROLE_PROTECTION,
    ROLE_WIN_CONDITION,
    ROLE_OVERRUN,
    ROLE_ANTHEM,
    ROLE_SACRIFICE_OUTLET,
    ROLE_DEATH_TRIGGER,
    ROLE_TOKEN_DOUBLER,
    ROLE_TOKEN_PRODUCER,
    ROLE_BLINK,
    ROLE_ETB_PAYOFF,
    ROLE_EVASION_GIVER,
    ROLE_EXTRA_COMBAT,
    ROLE_HASTE_ENABLER,
    ROLE_COST_REDUCER,
    ROLE_SPELL_COPY,
    ROLE_COMBAT_TRIGGER,
    ROLE_LEAVES_BATTLEFIELD,
    ROLE_GRAVEYARD_HATE,
    ROLE_CHANGELING,
    ROLE_TRIBAL_LORD,
    ROLE_COUNTER_STORE,
    ROLE_SHARED_TYPE,
    ROLE_LAND_TYPE_PAYOFF,
    ROLE_LIFEGAIN,
    ROLE_SYNERGY,
]


def classify_card(card: dict) -> list[str]:
    """Return all role tags for a card dict from the DB (or any dict with the right keys)."""
    roles: set[str] = set()
    name: str = card.get("name", "")
    oracle: str = card.get("oracle_text", "") or ""
    type_line: str = card.get("type_line", "") or ""
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

    # Changeling: check type line too (it's a keyword ability sometimes on type line)
    if re.search(r"\bchangeling\b", type_line, re.I):
        roles.add(ROLE_CHANGELING)

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
