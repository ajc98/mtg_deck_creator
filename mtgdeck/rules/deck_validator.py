from __future__ import annotations

from dataclasses import dataclass, field

from mtgdeck.models import BASIC_LAND_NAMES, ScryfallCard
from mtgdeck.rules.commander_rules import CommanderProfile
from mtgdeck.rules.color_identity import is_within_color_identity
from mtgdeck.rules.legality import is_commander_banned

RECOMMENDED_LAND_MIN = 34
RECOMMENDED_LAND_MAX = 38


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.valid = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_deck(
    profile: CommanderProfile,
    deck_cards: list[ScryfallCard],
) -> ValidationResult:
    result = ValidationResult()
    all_cards = [profile.card] + deck_cards
    commander_ci = profile.color_identity

    # 1. Total card count (commander included)
    if len(all_cards) != 100:
        result.fail(
            f"Deck has {len(all_cards)} cards; must have exactly 100 (including commander)."
        )

    # 2. Commander legality already validated when building CommanderProfile,
    #    but double-check the card wasn't banned after profile creation.
    if is_commander_banned(profile.card):
        result.fail(f"Commander '{profile.card.name}' is banned in Commander.")

    # 3. Singleton rule and per-card legality
    seen_names: dict[str, int] = {}
    for card in deck_cards:
        if is_commander_banned(card):
            result.fail(f"'{card.name}' is banned in Commander format.")

        if not is_within_color_identity(card.color_identity, commander_ci):
            result.fail(
                f"'{card.name}' has color identity {card.color_identity} "
                f"outside commander identity {commander_ci}."
            )

        if card.is_basic_land or card.allows_multiple_copies:
            continue
        count = seen_names.get(card.name, 0) + 1
        seen_names[card.name] = count
        if count > 1:
            result.fail(f"Singleton violation: '{card.name}' appears {count} times.")

    # 4. Land count heuristic
    land_count = sum(1 for c in deck_cards if c.is_land)
    if land_count < RECOMMENDED_LAND_MIN:
        result.warn(
            f"Only {land_count} lands — recommend {RECOMMENDED_LAND_MIN}–{RECOMMENDED_LAND_MAX}."
        )
    elif land_count > RECOMMENDED_LAND_MAX:
        result.warn(
            f"{land_count} lands — more than recommended {RECOMMENDED_LAND_MIN}–{RECOMMENDED_LAND_MAX}."
        )

    return result
