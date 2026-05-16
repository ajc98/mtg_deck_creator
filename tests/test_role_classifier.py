"""Tests for the role classifier."""
from __future__ import annotations

import pytest

from mtgdeck.scoring.role_classifier import (
    ROLE_BASIC_LAND, ROLE_BOARD_WIPE, ROLE_CARD_DRAW, ROLE_COUNTERSPELL,
    ROLE_GRAVEYARD_HATE, ROLE_LAND, ROLE_LAND_RAMP, ROLE_LIFEGAIN,
    ROLE_MANA_DORK, ROLE_MANA_ROCK, ROLE_PROTECTION, ROLE_RECURSION,
    ROLE_REMOVAL, ROLE_SACRIFICE_OUTLET, ROLE_TOKEN_PRODUCER,
    ROLE_WIN_CONDITION, classify_card, primary_role,
)


def _card(**kwargs) -> dict:
    defaults = {
        "name": "Test Card",
        "type_line": "Instant",
        "oracle_text": "",
        "cmc": 2.0,
        "is_land": False,
        "is_basic_land": False,
        "is_creature": False,
        "is_artifact": False,
        "is_enchantment": False,
        "is_instant": False,
        "is_sorcery": False,
    }
    defaults.update(kwargs)
    return defaults


class TestBasicLand:
    def test_basic_land_classified(self):
        card = _card(
            name="Forest",
            type_line="Basic Land — Forest",
            is_land=True,
            is_basic_land=True,
        )
        roles = classify_card(card)
        assert ROLE_BASIC_LAND in roles

    def test_basic_land_also_gets_land_role(self):
        card = _card(
            name="Swamp",
            type_line="Basic Land — Swamp",
            is_land=True,
            is_basic_land=True,
        )
        roles = classify_card(card)
        assert ROLE_LAND in roles


class TestLandRamp:
    def test_search_library_for_land(self):
        card = _card(
            type_line="Sorcery",
            oracle_text="Search your library for a basic Forest card and put it onto the battlefield.",
        )
        roles = classify_card(card)
        assert ROLE_LAND_RAMP in roles

    def test_fetch_land_pattern(self):
        card = _card(
            type_line="Sorcery",
            oracle_text="Search your library for a basic land card, put it onto the battlefield tapped.",
        )
        roles = classify_card(card)
        assert ROLE_LAND_RAMP in roles


class TestManaRock:
    def test_artifact_add_mana(self):
        card = _card(
            type_line="Artifact",
            oracle_text="{T}: Add {B}.",
            is_artifact=True,
        )
        roles = classify_card(card)
        assert ROLE_MANA_ROCK in roles

    def test_creature_add_mana_is_dork(self):
        card = _card(
            type_line="Creature — Elf Druid",
            oracle_text="{T}: Add {G}.",
            is_creature=True,
        )
        roles = classify_card(card)
        assert ROLE_MANA_DORK in roles


class TestCardDraw:
    def test_draw_a_card(self):
        card = _card(oracle_text="Draw a card.")
        roles = classify_card(card)
        assert ROLE_CARD_DRAW in roles

    def test_draw_two_cards(self):
        card = _card(oracle_text="Draw two cards.")
        roles = classify_card(card)
        assert ROLE_CARD_DRAW in roles

    def test_draw_x_cards(self):
        card = _card(oracle_text="Draw X cards.")
        roles = classify_card(card)
        assert ROLE_CARD_DRAW in roles


class TestRemoval:
    def test_destroy_target(self):
        card = _card(oracle_text="Destroy target creature.")
        roles = classify_card(card)
        assert ROLE_REMOVAL in roles

    def test_exile_target(self):
        card = _card(oracle_text="Exile target artifact or enchantment.")
        roles = classify_card(card)
        assert ROLE_REMOVAL in roles


class TestBoardWipe:
    def test_destroy_all(self):
        card = _card(oracle_text="Destroy all creatures.")
        roles = classify_card(card)
        assert ROLE_BOARD_WIPE in roles

    def test_exile_all(self):
        card = _card(oracle_text="Exile all artifacts.")
        roles = classify_card(card)
        assert ROLE_BOARD_WIPE in roles

    def test_deals_damage_to_each(self):
        card = _card(oracle_text="Lava Coil deals 4 damage to each creature.")
        roles = classify_card(card)
        assert ROLE_BOARD_WIPE in roles


class TestCounterspell:
    def test_counter_target_spell(self):
        card = _card(oracle_text="Counter target spell.")
        roles = classify_card(card)
        assert ROLE_COUNTERSPELL in roles


class TestProtection:
    def test_hexproof(self):
        card = _card(oracle_text="Target creature gains hexproof until end of turn.")
        roles = classify_card(card)
        assert ROLE_PROTECTION in roles

    def test_indestructible(self):
        card = _card(oracle_text="Creatures you control gain indestructible until end of turn.")
        roles = classify_card(card)
        assert ROLE_PROTECTION in roles


class TestRecursion:
    def test_return_from_graveyard(self):
        card = _card(oracle_text="Return target creature card from your graveyard to your hand.")
        roles = classify_card(card)
        assert ROLE_RECURSION in roles


class TestGraveyardHate:
    def test_exile_all_cards_from_graveyard(self):
        card = _card(oracle_text="Exile all cards from target player's graveyard.")
        roles = classify_card(card)
        assert ROLE_GRAVEYARD_HATE in roles


class TestSacrificeOutlet:
    def test_sacrifice_a_creature(self):
        card = _card(oracle_text="Sacrifice a creature: Add {B}{B}.")
        roles = classify_card(card)
        assert ROLE_SACRIFICE_OUTLET in roles


class TestTokenProducer:
    def test_create_token(self):
        card = _card(oracle_text="Create a 1/1 white Soldier creature token.")
        roles = classify_card(card)
        assert ROLE_TOKEN_PRODUCER in roles

    def test_put_token(self):
        card = _card(oracle_text="Put two 2/2 black Zombie creature tokens onto the battlefield.")
        roles = classify_card(card)
        assert ROLE_TOKEN_PRODUCER in roles


class TestWinCondition:
    def test_player_loses(self):
        card = _card(oracle_text="Target player loses the game.")
        roles = classify_card(card)
        assert ROLE_WIN_CONDITION in roles

    def test_you_win(self):
        card = _card(oracle_text="You win the game.")
        roles = classify_card(card)
        assert ROLE_WIN_CONDITION in roles

    def test_combat_damage_infect(self):
        card = _card(oracle_text="This creature has infect. It deals damage to players in the form of poison counters.")
        roles = classify_card(card)
        assert ROLE_WIN_CONDITION in roles


class TestPrimaryRole:
    def test_basic_land_is_highest_priority(self):
        roles = [ROLE_BASIC_LAND, ROLE_LAND, ROLE_MANA_ROCK]
        assert primary_role(roles) == ROLE_BASIC_LAND

    def test_empty_roles_returns_synergy(self):
        from mtgdeck.scoring.role_classifier import ROLE_SYNERGY
        assert primary_role([]) == ROLE_SYNERGY

    def test_win_condition_above_synergy(self):
        from mtgdeck.scoring.role_classifier import ROLE_SYNERGY
        roles = [ROLE_SYNERGY, ROLE_WIN_CONDITION]
        assert primary_role(roles) == ROLE_WIN_CONDITION
