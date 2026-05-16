import numpy as np
import pytest

from mtgdeck.embeddings.similarity import (
    cosine_similarity,
    cosine_similarity_batch,
    normalize_scores,
)


def test_identical_vectors():
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert cosine_similarity(a, a) == pytest.approx(1.0)


def test_orthogonal_vectors():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0], dtype=np.float32)
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_opposite_vectors():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([-1.0, 0.0], dtype=np.float32)
    assert cosine_similarity(a, b) == pytest.approx(-1.0)


def test_zero_vector_returns_zero():
    a = np.zeros(4, dtype=np.float32)
    b = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    assert cosine_similarity(a, b) == 0.0
    assert cosine_similarity(b, a) == 0.0


def test_batch_matches_single():
    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    matrix = np.array(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]], dtype=np.float32
    )
    scores = cosine_similarity_batch(query, matrix)
    assert scores[0] == pytest.approx(1.0, abs=1e-5)
    assert scores[1] == pytest.approx(0.0, abs=1e-5)
    assert scores[2] == pytest.approx(-1.0, abs=1e-5)


def test_batch_empty_matrix():
    query = np.array([1.0, 2.0], dtype=np.float32)
    matrix = np.empty((0, 2), dtype=np.float32)
    scores = cosine_similarity_batch(query, matrix)
    assert len(scores) == 0


def test_batch_zero_query():
    query = np.zeros(3, dtype=np.float32)
    matrix = np.ones((5, 3), dtype=np.float32)
    scores = cosine_similarity_batch(query, matrix)
    assert all(s == 0.0 for s in scores)


def test_batch_returns_highest_for_most_similar():
    query = np.array([1.0, 1.0, 0.0], dtype=np.float32)
    rows = np.array(
        [[1.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float32
    )
    scores = cosine_similarity_batch(query, rows)
    assert np.argmax(scores) == 0


def test_normalize_scores_range():
    scores = np.array([0.1, 0.5, 0.9], dtype=np.float32)
    normed = normalize_scores(scores)
    assert normed.min() == pytest.approx(0.0)
    assert normed.max() == pytest.approx(1.0)


def test_normalize_scores_constant_returns_zeros():
    scores = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    normed = normalize_scores(scores)
    assert all(v == 0.0 for v in normed)
