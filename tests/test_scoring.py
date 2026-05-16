"""Tests for the hybrid scoring system."""
from __future__ import annotations

import pytest

from mtgdeck.scoring.card_score import (
    CardScore, ScoreWeights,
    compute_edhrec_score, compute_role_need_score, compute_curve_score,
    score_card,
)
from mtgdeck.scoring.mana_curve import curve_counts, average_cmc, curve_health
from mtgdeck.scoring.role_classifier import ROLE_CARD_DRAW, ROLE_LAND, ROLE_REMOVAL


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_candidate(name="Sol Ring", cmc=1.0, roles=None, edhrec_rec=None, vector_score=0.0):
    from types import SimpleNamespace
    from mtgdeck.models import normalize_name
    return SimpleNamespace(
        normalized_name=normalize_name(name),
        name=name,
        card_row={"name": name, "cmc": cmc, "is_land": False},
        edhrec_rec=edhrec_rec,
        vector_score=vector_score,
        roles=roles or [],
    )


# ── ScoreWeights ─────────────────────────────────────────────────────────────


class TestScoreWeights:
    def test_default_weights_sum_to_one(self):
        w = ScoreWeights()
        total = w.edhrec + w.vector + w.role_need + w.synergy + w.curve
        assert abs(total - 1.0) < 1e-6

    def test_without_vector_sums_to_one(self):
        w = ScoreWeights().without_vector()
        total = w.edhrec + w.vector + w.role_need + w.synergy + w.curve
        assert abs(total - 1.0) < 1e-6

    def test_without_vector_zeroes_vector(self):
        w = ScoreWeights().without_vector()
        assert w.vector == 0.0


# ── compute_edhrec_score ──────────────────────────────────────────────────────


class TestComputeEdhrecScore:
    def test_none_rec_returns_zero(self):
        assert compute_edhrec_score(None) == 0.0

    def test_empty_rec_returns_low(self):
        score = compute_edhrec_score({})
        # synergy=0 maps to 0.5 via (0+1)/2; section default 0.55
        # result ≈ 0.30*0.5 + 0.10*0.55 = 0.205
        assert 0.0 <= score <= 0.30

    def test_high_deck_pct_gives_high_score(self):
        rec = {"deck_percentage": 90.0, "synergy_score": 0.5, "section": "synergy"}
        score = compute_edhrec_score(rec)
        assert score > 0.7

    def test_score_bounded_0_1(self):
        rec = {"deck_percentage": 150.0, "synergy_score": 5.0, "section": "synergy"}
        score = compute_edhrec_score(rec)
        assert 0.0 <= score <= 1.0


# ── compute_role_need_score ───────────────────────────────────────────────────


class TestComputeRoleNeedScore:
    def test_no_roles_returns_zero(self):
        assert compute_role_need_score([], {}, {ROLE_CARD_DRAW: 10}) == 0.0

    def test_completely_empty_target_returns_zero(self):
        assert compute_role_need_score([ROLE_CARD_DRAW], {}, {}) == 0.0

    def test_full_slot_returns_zero(self):
        score = compute_role_need_score(
            [ROLE_CARD_DRAW],
            {ROLE_CARD_DRAW: 10},
            {ROLE_CARD_DRAW: 10},
        )
        assert score == 0.0

    def test_empty_slot_returns_one(self):
        score = compute_role_need_score(
            [ROLE_CARD_DRAW],
            {},
            {ROLE_CARD_DRAW: 10},
        )
        assert score == 1.0

    def test_half_full_returns_half(self):
        score = compute_role_need_score(
            [ROLE_REMOVAL],
            {ROLE_REMOVAL: 5},
            {ROLE_REMOVAL: 10},
        )
        assert abs(score - 0.5) < 1e-6


# ── compute_curve_score ───────────────────────────────────────────────────────


class TestComputeCurveScore:
    def test_zero_cmc_moderate_score(self):
        assert compute_curve_score(0) == 0.50

    def test_two_cmc_is_best(self):
        assert compute_curve_score(2) == 1.00

    def test_three_cmc_is_best(self):
        assert compute_curve_score(3) == 1.00

    def test_high_cmc_penalized(self):
        assert compute_curve_score(7) == 0.10

    def test_scores_decrease_with_cmc(self):
        # 1 > 4 > 5 > 6 > 7
        assert compute_curve_score(1) > compute_curve_score(4)
        assert compute_curve_score(4) > compute_curve_score(5)
        assert compute_curve_score(5) > compute_curve_score(6)
        assert compute_curve_score(6) > compute_curve_score(7)


# ── score_card ────────────────────────────────────────────────────────────────


class TestScoreCard:
    def test_returns_card_score(self):
        candidate = _make_candidate()
        result = score_card(candidate, {}, {}, ScoreWeights())
        assert isinstance(result, CardScore)

    def test_final_score_bounded(self):
        candidate = _make_candidate(
            edhrec_rec={"deck_percentage": 95.0, "synergy_score": 1.0, "section": "synergy"},
            vector_score=1.0,
        )
        result = score_card(candidate, {}, {}, ScoreWeights())
        assert 0.0 <= result.final_score <= 1.0

    def test_edhrec_card_scores_higher_than_unknown(self):
        known = _make_candidate(
            edhrec_rec={"deck_percentage": 70.0, "synergy_score": 0.3, "section": "top"},
        )
        unknown = _make_candidate(name="Obscure Card")
        w = ScoreWeights()
        score_known   = score_card(known,   {}, {}, w).final_score
        score_unknown = score_card(unknown, {}, {}, w).final_score
        assert score_known > score_unknown

    def test_needed_role_boosts_score(self):
        candidate = _make_candidate(roles=[ROLE_CARD_DRAW])
        w = ScoreWeights()
        no_need  = score_card(candidate, {ROLE_CARD_DRAW: 10}, {ROLE_CARD_DRAW: 10}, w).final_score
        has_need = score_card(candidate, {},                    {ROLE_CARD_DRAW: 10}, w).final_score
        assert has_need > no_need

    def test_explanation_is_non_empty(self):
        candidate = _make_candidate()
        result = score_card(candidate, {}, {}, ScoreWeights())
        assert result.explanation


# ── mana_curve ────────────────────────────────────────────────────────────────


class TestCurveCounts:
    def test_empty(self):
        assert curve_counts([]) == {}

    def test_basic_counts(self):
        counts = curve_counts([1, 2, 2, 3, 7, 8])
        assert counts[1] == 1
        assert counts[2] == 2
        assert counts[3] == 1
        assert counts[7] == 2  # 7 and 8 both bucketed to 7

    def test_high_cmc_bucketed(self):
        counts = curve_counts([10, 12, 15])
        assert counts.get(7, 0) == 3


class TestAverageCmc:
    def test_excludes_zero(self):
        avg = average_cmc([0, 0, 2, 4])
        assert abs(avg - 3.0) < 1e-6

    def test_empty_returns_zero(self):
        assert average_cmc([]) == 0.0

    def test_all_zero_returns_zero(self):
        assert average_cmc([0, 0, 0]) == 0.0


class TestCurveHealth:
    def test_warns_on_too_many_expensive_cards(self):
        # Mostly 6+ CMC cards — should trigger a warning
        cmcs = [6.0] * 20 + [2.0] * 5
        health = curve_health(cmcs)
        assert any("expensive" in w.lower() or "high" in w.lower() for w in health["warnings"])

    def test_no_warnings_on_good_curve(self):
        cmcs = [1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 2.0, 3.0, 2.0, 1.0]
        health = curve_health(cmcs)
        assert health["average"] < 4.0
