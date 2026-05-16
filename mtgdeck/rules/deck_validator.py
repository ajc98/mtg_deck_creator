from __future__ import annotations

import json
from dataclasses import dataclass, field

from mtgdeck.models import BASIC_LAND_NAMES, SINGLETON_OVERRIDE_RE, ScryfallCard
from mtgdeck.rules.commander_rules import CommanderProfile
from mtgdeck.rules.color_identity import is_within_color_identity

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


def _card_name(card) -> str:
    return card.name if isinstance(card, ScryfallCard) else card.get("name", "")


def _card_ci(card) -> list[str]:
    if isinstance(card, ScryfallCard):
        return card.color_identity
    raw = card.get("color_identity") or "[]"
    return json.loads(raw) if isinstance(raw, str) else list(raw)


def _card_is_basic_land(card) -> bool:
    if isinstance(card, ScryfallCard):
        return card.is_basic_land
    return bool(card.get("is_basic_land")) or card.get("name", "") in BASIC_LAND_NAMES


def _card_is_land(card) -> bool:
    if isinstance(card, ScryfallCard):
        return card.is_land
    return bool(card.get("is_land"))


def _card_allows_multiple(card) -> bool:
    if isinstance(card, ScryfallCard):
        return card.allows_multiple_copies
    oracle = card.get("oracle_text") or ""
    return bool(SINGLETON_OVERRIDE_RE.search(oracle))


def _card_is_banned(card) -> bool:
    if isinstance(card, ScryfallCard):
        return card.legalities.get("commander") == "banned"
    # DB rows store legal_commander as a boolean (False = banned/not legal)
    return not bool(card.get("legal_commander", True))


def validate_deck(
    profile: CommanderProfile,
    deck_cards: list,   # list[ScryfallCard | dict]
) -> ValidationResult:
    """Validate a 99-card deck list (excluding commander) against Commander rules."""
    result = ValidationResult()
    commander_ci = profile.color_identity

    # 1. Total card count (commander + 99)
    total = 1 + len(deck_cards)
    if total != 100:
        result.fail(
            f"Deck has {total} cards; must have exactly 100 (including commander)."
        )

    # 2. Commander ban check
    if profile.card.legalities.get("commander") == "banned":
        result.fail(f"Commander '{profile.card.name}' is banned in Commander.")

    # 3. Singleton rule and per-card legality
    seen_names: dict[str, int] = {}
    for card in deck_cards:
        name = _card_name(card)

        if _card_is_banned(card):
            result.fail(f"'{name}' is banned in Commander format.")

        if not is_within_color_identity(_card_ci(card), commander_ci):
            result.fail(
                f"'{name}' has color identity {_card_ci(card)} "
                f"outside commander identity {commander_ci}."
            )

        if _card_is_basic_land(card) or _card_allows_multiple(card):
            continue
        count = seen_names.get(name, 0) + 1
        seen_names[name] = count
        if count > 1:
            result.fail(f"Singleton violation: '{name}' appears {count} times.")

    # 4. Land count heuristic
    land_count = sum(1 for c in deck_cards if _card_is_land(c))
    if land_count < RECOMMENDED_LAND_MIN:
        result.warn(
            f"Only {land_count} lands — recommend {RECOMMENDED_LAND_MIN}–{RECOMMENDED_LAND_MAX}."
        )
    elif land_count > RECOMMENDED_LAND_MAX:
        result.warn(
            f"{land_count} lands — more than recommended {RECOMMENDED_LAND_MIN}–{RECOMMENDED_LAND_MAX}."
        )

    return result
