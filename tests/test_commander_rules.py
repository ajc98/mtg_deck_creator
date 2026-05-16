import pytest

from mtgdeck.models import ScryfallCard
from mtgdeck.rules.commander_rules import is_legal_commander


def _make_card(**kwargs) -> ScryfallCard:
    defaults = dict(
        oracle_id="test-oracle-id",
        id="test-scryfall-id",
        name="Test Card",
        type_line="Legendary Creature — Human",
        oracle_text="",
        mana_cost="{1}{B}",
        cmc=2.0,
        color_identity=["B"],
        legalities={"commander": "legal"},
    )
    defaults.update(kwargs)
    return ScryfallCard.model_validate(defaults)


def test_legendary_creature_is_legal_commander():
    card = _make_card()
    assert is_legal_commander(card)


def test_nonlegendary_creature_is_not_commander():
    card = _make_card(type_line="Creature — Human", legalities={"commander": "not_legal"})
    assert not is_legal_commander(card)


def test_banned_card_is_not_commander():
    card = _make_card(legalities={"commander": "banned"})
    assert not is_legal_commander(card)


def test_partner_card_is_legal():
    card = _make_card(
        type_line="Legendary Creature — Human Wizard",
        oracle_text="Partner\nWhen ~ enters the battlefield, draw a card.",
    )
    assert is_legal_commander(card)


def test_choose_background_is_legal():
    card = _make_card(
        type_line="Legendary Creature — Human Soldier",
        oracle_text="Choose a Background",
    )
    assert is_legal_commander(card)


def test_planeswalker_with_can_be_commander_text():
    card = _make_card(
        type_line="Legendary Planeswalker — Teferi",
        oracle_text="Teferi, Temporal Pilgrim can be your commander.",
        legalities={"commander": "legal"},
    )
    assert is_legal_commander(card)


def test_normal_planeswalker_is_not_commander():
    card = _make_card(
        type_line="Legendary Planeswalker — Chandra",
        oracle_text="+1: Add {R}{R}.",
        legalities={"commander": "not_legal"},
    )
    assert not is_legal_commander(card)


def test_scryfall_legality_is_required():
    # Even if the type line looks right, non-legal means no.
    card = _make_card(legalities={"commander": "not_legal"})
    assert not is_legal_commander(card)
