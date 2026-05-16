from __future__ import annotations

import re

from pydantic import BaseModel, Field

BASIC_LAND_NAMES: frozenset[str] = frozenset(
    {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}
)

# Cards whose Oracle text allows any number of copies in a deck
SINGLETON_OVERRIDE_RE = re.compile(r"[Aa] deck can have any number of cards named")


def normalize_name(name: str) -> str:
    name = name.strip().lower()
    name = name.replace("’", "'").replace("‘", "'")  # curly apostrophes → straight
    name = re.sub(r"[^\w\s',\-]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


class ScryfallCard(BaseModel):
    oracle_id: str
    id: str  # scryfall_id
    name: str
    type_line: str = ""
    oracle_text: str = ""
    mana_cost: str = ""
    cmc: float = 0.0
    colors: list[str] = Field(default_factory=list)
    color_identity: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    legalities: dict[str, str] = Field(default_factory=dict)
    layout: str = ""
    produced_mana: list[str] | None = None
    edhrec_rank: int | None = None
    card_faces: list[dict] | None = None

    @property
    def normalized_name(self) -> str:
        return normalize_name(self.name)

    @property
    def is_basic_land(self) -> bool:
        return self.name in BASIC_LAND_NAMES

    @property
    def is_land(self) -> bool:
        return "Land" in self.type_line

    @property
    def is_creature(self) -> bool:
        return "Creature" in self.type_line

    @property
    def is_artifact(self) -> bool:
        return "Artifact" in self.type_line

    @property
    def is_enchantment(self) -> bool:
        return "Enchantment" in self.type_line

    @property
    def is_instant(self) -> bool:
        return "Instant" in self.type_line

    @property
    def is_sorcery(self) -> bool:
        return "Sorcery" in self.type_line

    @property
    def is_planeswalker(self) -> bool:
        return "Planeswalker" in self.type_line

    @property
    def commander_legal(self) -> bool:
        return self.legalities.get("commander") == "legal"

    @property
    def allows_multiple_copies(self) -> bool:
        return bool(SINGLETON_OVERRIDE_RE.search(self.oracle_text))

    def full_oracle_text(self) -> str:
        """Merge face texts for multi-faced cards (DFCs, split cards, etc.)."""
        if self.card_faces:
            return " // ".join(
                face.get("oracle_text", "") for face in self.card_faces if face.get("oracle_text")
            )
        return self.oracle_text
