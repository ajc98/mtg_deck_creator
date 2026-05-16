import pytest

from mtgdeck.models import ScryfallCard
from mtgdeck.rules.commander_rules import CommanderProfile
from mtgdeck.rules.deck_validator import validate_deck


def _card(**kwargs) -> ScryfallCard:
    defaults = dict(
        oracle_id="oid",
        id="sid",
        name="Generic Card",
        type_line="Instant",
        oracle_text="",
        mana_cost="{1}{B}",
        cmc=2.0,
        color_identity=["B"],
        legalities={"commander": "legal"},
    )
    defaults.update(kwargs)
    return ScryfallCard.model_validate(defaults)


def _commander() -> ScryfallCard:
    return _card(
        oracle_id="cmd-oid",
        id="cmd-sid",
        name="K'rrik, Son of Yawgmoth",
        type_line="Legendary Creature — Phyrexian Horror",
        color_identity=["B"],
    )


def _build_deck(commander: ScryfallCard, size: int = 99) -> list[ScryfallCard]:
    swamps = [
        _card(
            oracle_id=f"swamp-{i}",
            id=f"swamp-{i}",
            name="Swamp",
            type_line="Basic Land — Swamp",
            mana_cost="",
            cmc=0.0,
            color_identity=["B"],
        )
        for i in range(36)
    ]
    rest = [
        _card(
            oracle_id=f"card-{i}",
            id=f"card-{i}",
            name=f"Spell {i}",
            color_identity=["B"],
        )
        for i in range(size - 36)
    ]
    return swamps + rest


def test_valid_100_card_deck():
    cmd = _commander()
    profile = CommanderProfile(card=cmd)
    deck = _build_deck(cmd, size=99)
    result = validate_deck(profile, deck)
    assert result.valid
    assert not result.errors


def test_too_few_cards():
    cmd = _commander()
    profile = CommanderProfile(card=cmd)
    deck = _build_deck(cmd, size=50)
    result = validate_deck(profile, deck)
    assert not result.valid
    assert any("100" in e for e in result.errors)


def test_color_identity_violation():
    cmd = _commander()  # mono black
    profile = CommanderProfile(card=cmd)
    deck = _build_deck(cmd, size=98)
    illegal = _card(
        oracle_id="illegal-oid",
        id="illegal-sid",
        name="White Illegal Card",
        color_identity=["W"],
    )
    deck.append(illegal)
    result = validate_deck(profile, deck)
    assert not result.valid
    assert any("White Illegal Card" in e for e in result.errors)


def test_singleton_violation():
    cmd = _commander()
    profile = CommanderProfile(card=cmd)
    deck = _build_deck(cmd, size=97)
    dupe = _card(oracle_id="dupe-oid", id="dupe-sid", name="Unique Spell", color_identity=["B"])
    dupe2 = _card(oracle_id="dupe-oid2", id="dupe-sid2", name="Unique Spell", color_identity=["B"])
    deck += [dupe, dupe2]
    result = validate_deck(profile, deck)
    assert not result.valid
    assert any("Unique Spell" in e for e in result.errors)


def test_basic_land_singleton_exempt():
    cmd = _commander()
    profile = CommanderProfile(card=cmd)
    # All 99 slots are Swamps — should be legal
    swamps = [
        _card(
            oracle_id=f"swamp-{i}",
            id=f"swamp-{i}",
            name="Swamp",
            type_line="Basic Land — Swamp",
            mana_cost="",
            cmc=0.0,
            color_identity=["B"],
        )
        for i in range(99)
    ]
    result = validate_deck(profile, swamps)
    assert result.valid
    assert not result.errors
