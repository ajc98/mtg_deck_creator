import json

import numpy as np
import pytest

from mtgdeck.embeddings.embed_cards import build_card_search_text, resolve_model_name
from mtgdeck.embeddings.vector_search import (
    EmbeddingIndex,
    SearchResult,
    build_commander_query,
    build_role_query,
    search,
)


# ---------------------------------------------------------------------------
# build_card_search_text
# ---------------------------------------------------------------------------


def _card_row(**kwargs) -> dict:
    defaults = dict(
        name="Vilis, Broker of Blood",
        type_line="Legendary Creature — Demon",
        mana_cost="{5}{B}{B}{B}",
        cmc=8.0,
        oracle_text="Flying\nWhenever you pay life, draw that many cards.",
        keywords='["Flying"]',
    )
    defaults.update(kwargs)
    return defaults


def test_build_search_text_includes_name():
    text = build_card_search_text(_card_row())
    assert "Vilis, Broker of Blood" in text


def test_build_search_text_includes_oracle_text():
    text = build_card_search_text(_card_row())
    assert "draw that many cards" in text


def test_build_search_text_includes_mana_value():
    text = build_card_search_text(_card_row(cmc=8.0))
    assert "Mana Value: 8" in text


def test_build_search_text_no_keywords_field():
    row = _card_row()
    row["keywords"] = None
    text = build_card_search_text(row)
    assert "Keywords" not in text


def test_build_search_text_empty_keywords_list():
    row = _card_row(keywords=json.dumps([]))
    text = build_card_search_text(row)
    assert "Keywords" not in text


def test_build_search_text_keywords_present():
    row = _card_row(keywords=json.dumps(["Flying", "Deathtouch"]))
    text = build_card_search_text(row)
    assert "Keywords: Flying, Deathtouch" in text


# ---------------------------------------------------------------------------
# resolve_model_name
# ---------------------------------------------------------------------------


def test_resolve_local_alias():
    assert resolve_model_name("local") == "all-MiniLM-L6-v2"


def test_resolve_local_large_alias():
    assert resolve_model_name("local-large") == "all-mpnet-base-v2"


def test_resolve_passthrough():
    assert resolve_model_name("my-custom/model") == "my-custom/model"


# ---------------------------------------------------------------------------
# query builders
# ---------------------------------------------------------------------------


def test_build_commander_query_contains_name():
    q = build_commander_query("K'rrik, Son of Yawgmoth", "Pay life to cast spells.")
    assert "K'rrik" in q
    assert "Pay life" in q


def test_build_commander_query_with_themes():
    q = build_commander_query("X", "text", themes=["lifepay", "sacrifice"])
    assert "lifepay" in q
    assert "sacrifice" in q


def test_build_role_query():
    q = build_role_query("ramp", ["B"])
    assert "ramp" in q
    assert "B" in q


# ---------------------------------------------------------------------------
# search() — pure numpy, no model required
# ---------------------------------------------------------------------------


def _make_index(n: int = 5, dims: int = 4) -> EmbeddingIndex:
    rng = np.random.default_rng(42)
    matrix = rng.standard_normal((n, dims)).astype(np.float32)
    return EmbeddingIndex(
        normalized_names=[f"card-{i}" for i in range(n)],
        names=[f"Card {i}" for i in range(n)],
        type_lines=["Instant"] * n,
        color_identities=[["B"]] * n,
        cmcs=[float(i) for i in range(n)],
        is_lands=[False] * n,
        is_creatures=[i % 2 == 0 for i in range(n)],
        oracle_texts=[""] * n,
        matrix=matrix,
    )


def test_search_returns_top_k():
    idx = _make_index(10, 4)
    query = idx.matrix[0].copy()
    results = search(idx, query, top_k=3)
    assert len(results) <= 3


def test_search_most_similar_is_first():
    idx = _make_index(5, 4)
    # Query is identical to row 2 — it should be ranked #1
    query = idx.matrix[2].copy()
    results = search(idx, query)
    assert results[0].name == "Card 2"


def test_search_color_identity_filter():
    idx = _make_index(4, 4)
    # Override color identities: only card 1 is white
    idx.color_identities[1] = ["W"]
    query = np.ones(4, dtype=np.float32)
    results = search(idx, query, commander_ci=["B"])
    names = [r.name for r in results]
    assert "Card 1" not in names


def test_search_exclude_names():
    idx = _make_index(5, 4)
    query = idx.matrix[0].copy()
    results = search(idx, query, exclude_names={"Card 0"})
    assert all(r.name != "Card 0" for r in results)


def test_search_exclude_lands():
    idx = _make_index(4, 4)
    idx.is_lands[0] = True
    query = np.ones(4, dtype=np.float32)
    results = search(idx, query, exclude_lands=True)
    assert all(not r.is_land for r in results)


def test_search_lands_only():
    idx = _make_index(4, 4)
    idx.is_lands[2] = True
    query = np.ones(4, dtype=np.float32)
    results = search(idx, query, lands_only=True)
    assert all(r.is_land for r in results)


def test_search_min_score_filters_low_similarity():
    idx = _make_index(10, 8)
    # Use a query orthogonal to most rows — many will have low scores
    query = np.zeros(8, dtype=np.float32)
    query[0] = 1.0
    results = search(idx, query, min_score=0.99)
    # Very few (possibly zero) rows will have cosine ≥ 0.99 to a unit vector
    assert len(results) < 10


def test_search_empty_index():
    idx = EmbeddingIndex(
        normalized_names=[],
        names=[],
        type_lines=[],
        color_identities=[],
        cmcs=[],
        is_lands=[],
        is_creatures=[],
        oracle_texts=[],
        matrix=np.empty((0, 4), dtype=np.float32),
    )
    results = search(idx, np.ones(4, dtype=np.float32))
    assert results == []


def test_search_normalizes_scores():
    idx = _make_index(5, 4)
    query = idx.matrix[0].copy()
    results = search(idx, query)
    assert results[0].similarity_score_norm == pytest.approx(1.0)
    assert results[-1].similarity_score_norm == pytest.approx(0.0)
