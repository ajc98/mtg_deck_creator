from __future__ import annotations

from mtgdeck.models import BASIC_LAND_NAMES, ScryfallCard
from mtgdeck.rules.color_identity import is_within_color_identity


def is_commander_banned(card: ScryfallCard) -> bool:
    return card.legalities.get("commander") == "banned"


def passes_color_identity(card: ScryfallCard, commander_ci: list[str]) -> bool:
    return is_within_color_identity(card.color_identity, commander_ci)


def is_singleton_legal(
    card: ScryfallCard,
    names_in_deck: list[str],
) -> bool:
    """Return True if adding this card does not violate the singleton rule.

    Basic lands and cards with explicit any-number override are exempt.
    """
    if card.is_basic_land or card.allows_multiple_copies:
        return True
    return card.name not in names_in_deck
