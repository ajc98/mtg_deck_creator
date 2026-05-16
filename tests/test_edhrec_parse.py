import pytest

from mtgdeck.data.edhrec_parse import slugify, parse_edhrec_json, best_recommendation_per_card


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, expected",
    [
        ("K'rrik, Son of Yawgmoth", "krrik-son-of-yawgmoth"),
        ("Atraxa, Praetors' Voice", "atraxa-praetors-voice"),
        ("Omo, Queen of Vesuva", "omo-queen-of-vesuva"),
        ("Giada, Font of Hope", "giada-font-of-hope"),
        ("Shorikai, Genesis Engine", "shorikai-genesis-engine"),
        ("Ob Nixilis, the Adversary", "ob-nixilis-the-adversary"),
    ],
)
def test_slugify(name, expected):
    assert slugify(name) == expected


# ---------------------------------------------------------------------------
# parse_edhrec_json
# ---------------------------------------------------------------------------


def _fake_edhrec_json(cardlists: list[dict]) -> dict:
    """Wrap cardlists in the standard EDHREC Next.js JSON envelope."""
    return {"container": {"json_dict": {"cardlists": cardlists}}}


def test_parse_basic_record():
    data = _fake_edhrec_json(
        [
            {
                "header": "High Synergy Cards",
                "tag": "synergy",
                "cardviews": [
                    {
                        "name": "Vilis, Broker of Blood",
                        "synergy": 0.52,
                        "num_decks": 5000,
                        "potential_decks": 10000,
                        "salt": 0.12,
                        "url": "/cards/vilis-broker-of-blood",
                    }
                ],
            }
        ]
    )
    records = parse_edhrec_json(data, "K'rrik, Son of Yawgmoth", "https://example.com")
    assert len(records) == 1
    r = records[0]
    assert r["card_name"] == "Vilis, Broker of Blood"
    assert r["section"] == "synergy"
    assert r["theme"] == "High Synergy Cards"
    assert r["deck_percentage"] == pytest.approx(50.0)
    assert r["deck_count"] == 5000
    assert r["synergy_score"] == pytest.approx(0.52)
    assert r["salt_score"] == pytest.approx(0.12)


def test_parse_zero_potential_decks():
    data = _fake_edhrec_json(
        [
            {
                "header": "New Cards",
                "tag": "new",
                "cardviews": [{"name": "Brand New Card", "num_decks": 0, "potential_decks": 0}],
            }
        ]
    )
    records = parse_edhrec_json(data, "Commander", "http://x")
    assert records[0]["deck_percentage"] == 0.0


def test_parse_skips_none_cardviews():
    data = _fake_edhrec_json(
        [
            {
                "header": "Top Cards",
                "tag": "top",
                "cardviews": [None, {"name": "Sol Ring", "num_decks": 100, "potential_decks": 200}],
            }
        ]
    )
    records = parse_edhrec_json(data, "X", "http://x")
    assert len(records) == 1
    assert records[0]["card_name"] == "Sol Ring"


def test_parse_multiple_sections():
    data = _fake_edhrec_json(
        [
            {
                "header": "Creatures",
                "tag": "creatures",
                "cardviews": [{"name": "Phyrexian Obliterator", "num_decks": 80, "potential_decks": 100}],
            },
            {
                "header": "Instants",
                "tag": "instants",
                "cardviews": [{"name": "Dark Ritual", "num_decks": 90, "potential_decks": 100}],
            },
        ]
    )
    records = parse_edhrec_json(data, "X", "http://x")
    assert len(records) == 2
    sections = {r["section"] for r in records}
    assert sections == {"creatures", "instants"}


def test_parse_fallback_paths():
    # Some EDHREC responses skip the container wrapper
    data = {"cardlists": [{"header": "Top", "tag": "top", "cardviews": [{"name": "Card A", "num_decks": 1, "potential_decks": 2}]}]}
    records = parse_edhrec_json(data, "X", "http://x")
    assert len(records) == 1


def test_parse_empty_response():
    records = parse_edhrec_json({}, "X", "http://x")
    assert records == []


# ---------------------------------------------------------------------------
# best_recommendation_per_card
# ---------------------------------------------------------------------------


def test_best_recommendation_deduplicates():
    records = [
        {"normalized_card_name": "sol-ring", "card_name": "Sol Ring", "deck_percentage": 70.0, "section": "top"},
        {"normalized_card_name": "sol-ring", "card_name": "Sol Ring", "deck_percentage": 65.0, "section": "mana"},
    ]
    result = best_recommendation_per_card(records)
    assert len(result) == 1
    assert result[0]["deck_percentage"] == 70.0
    assert result[0]["section"] == "top"


def test_best_recommendation_preserves_distinct_cards():
    records = [
        {"normalized_card_name": "sol-ring", "card_name": "Sol Ring", "deck_percentage": 70.0},
        {"normalized_card_name": "dark-ritual", "card_name": "Dark Ritual", "deck_percentage": 55.0},
    ]
    result = best_recommendation_per_card(records)
    assert len(result) == 2
