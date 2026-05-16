from __future__ import annotations

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D vectors. Returns 0.0 for zero vectors."""
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def cosine_similarity_batch(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity between *query* (1-D) and every row of *matrix* (2-D).

    Returns a 1-D array of shape (n,) where n = matrix.shape[0].
    All values are in [-1, 1]; zero vectors yield 0.0.
    """
    query_norm = float(np.linalg.norm(query))
    if query_norm == 0.0 or matrix.shape[0] == 0:
        return np.zeros(matrix.shape[0], dtype=np.float32)

    query_unit = query / query_norm

    row_norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    # Replace zeros to avoid divide-by-zero; those rows will produce near-0 dot product anyway
    row_norms = np.where(row_norms == 0.0, 1e-10, row_norms)
    matrix_unit = matrix / row_norms

    return (matrix_unit @ query_unit).astype(np.float32)


def normalize_scores(scores: np.ndarray) -> np.ndarray:
    """Min-max normalize scores to [0, 1]. Returns zeros if all scores are equal."""
    lo, hi = scores.min(), scores.max()
    if hi == lo:
        return np.zeros_like(scores, dtype=np.float32)
    return ((scores - lo) / (hi - lo)).astype(np.float32)
