from __future__ import annotations

COLOR_NAMES: dict[str, str] = {
    "W": "White",
    "U": "Blue",
    "B": "Black",
    "R": "Red",
    "G": "Green",
    "C": "Colorless",
}

COLOR_ORDER = ["W", "U", "B", "R", "G"]


def is_within_color_identity(
    card_ci: list[str], commander_ci: list[str]
) -> bool:
    """Return True if every color in card_ci is present in commander_ci.

    Colorless cards (empty list or only 'C') are legal in any deck.
    """
    effective = [c for c in card_ci if c != "C"]
    return set(effective).issubset(set(commander_ci))


def format_color_identity(ci: list[str]) -> str:
    ordered = [c for c in COLOR_ORDER if c in ci]
    extras = [c for c in ci if c not in COLOR_ORDER]
    return "".join(ordered + extras) or "C"


def color_identity_name(ci: list[str]) -> str:
    if not ci or ci == ["C"]:
        return "Colorless"
    names = [COLOR_NAMES.get(c, c) for c in ci if c in COLOR_NAMES]
    return "/".join(names)
