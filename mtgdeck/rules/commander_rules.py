from __future__ import annotations

import re
from dataclasses import dataclass, field

from mtgdeck.models import ScryfallCard

# Patterns that grant commander eligibility without being Legendary Creatures
_PARTNER_RE = re.compile(r"\bPartner\b")
_FRIENDS_FOREVER_RE = re.compile(r"\bFriends forever\b", re.IGNORECASE)
_CHOOSE_BG_RE = re.compile(r"\bChoose a Background\b", re.IGNORECASE)
_DOCTORS_COMPANION_RE = re.compile(r"\bDoctor's companion\b", re.IGNORECASE)


def is_legal_commander(card: ScryfallCard) -> bool:
    """Return True if this card is a legal Commander.

    Scryfall's legalities.commander field is the primary authority.
    Additionally the card must pass the commander-designation check:
    it must be a Legendary Creature, or a planeswalker/other permanent
    with an ability that grants commander status.
    """
    if card.legalities.get("commander") != "legal":
        return False

    type_line = card.type_line
    oracle = card.full_oracle_text()

    if "Legendary" in type_line and "Creature" in type_line:
        return True

    if "Legendary" in type_line and "Planeswalker" in type_line:
        if "can be your commander" in oracle.lower():
            return True

    # Background enchantments, Partner partners, etc.
    if _PARTNER_RE.search(oracle):
        return True
    if _FRIENDS_FOREVER_RE.search(oracle):
        return True
    if _CHOOSE_BG_RE.search(oracle):
        return True
    if _DOCTORS_COMPANION_RE.search(oracle):
        return True

    # Legendary permanent with explicit "can be your commander" text
    if "Legendary" in type_line and "can be your commander" in oracle.lower():
        return True

    return False


@dataclass
class CommanderProfile:
    card: ScryfallCard
    partner: ScryfallCard | None = None
    color_identity: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        ci = set(self.card.color_identity)
        if self.partner:
            ci |= set(self.partner.color_identity)
        self.color_identity = sorted(ci)

    @property
    def name(self) -> str:
        if self.partner:
            return f"{self.card.name} + {self.partner.name}"
        return self.card.name
