"""Format and write decklists to text files."""
from __future__ import annotations

from pathlib import Path


def format_decklist(commander_name: str, cards: list[dict]) -> str:
    """Return a plain-text decklist in standard 1x Name format."""
    lines: list[str] = [f"Commander\n1 {commander_name}\n"]

    # Group cards by type category
    lands    = [c for c in cards if c.get("is_basic_land")]
    ut_lands = [c for c in cards if c.get("is_land") and not c.get("is_basic_land")]
    creatures = [c for c in cards if c.get("is_creature") and not c.get("is_land")]
    artifacts = [c for c in cards if c.get("is_artifact") and not c.get("is_creature") and not c.get("is_land")]
    enchants  = [c for c in cards if c.get("is_enchantment") and not c.get("is_creature") and not c.get("is_artifact") and not c.get("is_land")]
    instants  = [c for c in cards if c.get("is_instant")]
    sorceries = [c for c in cards if c.get("is_sorcery")]
    other     = [
        c for c in cards
        if not any(c.get(k) for k in ("is_land","is_creature","is_artifact","is_enchantment","is_instant","is_sorcery"))
    ]

    def _section(header: str, group: list[dict]) -> None:
        if not group:
            return
        # Count multiples (basic lands)
        counts: dict[str, int] = {}
        for card in group:
            counts[card["name"]] = counts.get(card["name"], 0) + 1
        lines.append(header)
        seen: set[str] = set()
        for card in group:
            n = card["name"]
            if n in seen:
                continue
            seen.add(n)
            lines.append(f"{counts[n]} {n}")
        lines.append("")

    _section("Lands", ut_lands + lands)
    _section("Creatures", creatures)
    _section("Artifacts", artifacts)
    _section("Enchantments", enchants)
    _section("Instants", instants)
    _section("Sorceries", sorceries)
    _section("Other", other)

    return "\n".join(lines)


def write_decklist(path: Path, commander_name: str, cards: list[dict]) -> None:
    text = format_decklist(commander_name, cards)
    path.write_text(text, encoding="utf-8")
