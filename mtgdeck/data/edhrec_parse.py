from __future__ import annotations

import re

from mtgdeck.models import normalize_name


def slugify(name: str) -> str:
    """Convert a commander name to an EDHREC URL slug.

    Examples:
        "K'rrik, Son of Yawgmoth"  → "krrik-son-of-yawgmoth"
        "Atraxa, Praetors' Voice"  → "atraxa-praetors-voice"
        "Omo, Queen of Vesuva"     → "omo-queen-of-vesuva"
    """
    s = name.lower()
    s = re.sub(r"[',\.]", "", s)          # strip apostrophes, commas, periods
    s = re.sub(r"[^a-z0-9\s\-]", "", s)  # drop remaining non-slug chars
    s = re.sub(r"[\s\-]+", "-", s.strip())
    return s


def _dig(data: dict, *keys: str):
    """Navigate nested dicts; return None if any key is missing."""
    node = data
    for k in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(k)
    return node


def _extract_cardlists(data: dict) -> list[dict]:
    """Return the cardlists array from wherever EDHREC hides it."""
    candidates = [
        _dig(data, "container", "json_dict", "cardlists"),
        _dig(data, "json_dict", "cardlists"),
        _dig(data, "cardlists"),
    ]
    for c in candidates:
        if isinstance(c, list) and c:
            return c
    return []


def parse_edhrec_json(
    data: dict,
    commander_name: str,
    source_url: str,
) -> list[dict]:
    """Parse an EDHREC JSON response into a flat list of recommendation records.

    Each record maps one card to one section (a card may appear in multiple
    sections, which is intentional — section context matters for scoring).
    """
    cardlists = _extract_cardlists(data)
    records: list[dict] = []

    for card_list in cardlists:
        section: str = card_list.get("tag", "")
        theme: str = card_list.get("header", "")
        cardviews: list[dict] = card_list.get("cardviews", [])

        for cv in cardviews:
            # cardviews can contain None entries as spacers on EDHREC
            if not isinstance(cv, dict):
                continue
            card_name: str = (cv.get("name") or "").strip()
            if not card_name:
                continue

            num_decks: int = int(cv.get("num_decks") or 0)
            potential_decks: int = int(cv.get("potential_decks") or 0)
            deck_pct = (
                round(num_decks / potential_decks * 100, 4)
                if potential_decks > 0
                else 0.0
            )

            raw_synergy = cv.get("synergy")
            raw_salt = cv.get("salt")

            records.append(
                {
                    "commander_name": commander_name,
                    "card_name": card_name,
                    "normalized_card_name": normalize_name(card_name),
                    "section": section,
                    "theme": theme,
                    "synergy_score": float(raw_synergy) if raw_synergy is not None else None,
                    "deck_percentage": deck_pct,
                    "deck_count": num_decks,
                    "salt_score": float(raw_salt) if raw_salt is not None else None,
                    "source_url": source_url,
                }
            )

    return records


def best_recommendation_per_card(records: list[dict]) -> list[dict]:
    """Deduplicate by card name, keeping the record with the highest deck_percentage."""
    seen: dict[str, dict] = {}
    for r in records:
        key = r["normalized_card_name"]
        if key not in seen or r["deck_percentage"] > seen[key]["deck_percentage"]:
            seen[key] = r
    return list(seen.values())
