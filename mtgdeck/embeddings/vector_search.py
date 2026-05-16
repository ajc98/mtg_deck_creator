from __future__ import annotations

import json
from dataclasses import dataclass, field

import duckdb
import numpy as np

from mtgdeck.embeddings.similarity import cosine_similarity_batch


@dataclass
class SearchResult:
    normalized_name: str
    name: str
    type_line: str
    color_identity: list[str]
    cmc: float
    is_land: bool
    is_creature: bool
    oracle_text: str
    similarity_score: float  # raw cosine, −1..1
    similarity_score_norm: float = 0.0  # min-max normalized 0..1 within result set


@dataclass
class EmbeddingIndex:
    """In-memory index of all card embeddings for a model."""
    normalized_names: list[str]
    names: list[str]
    type_lines: list[str]
    color_identities: list[list[str]]  # parsed from JSON
    cmcs: list[float]
    is_lands: list[bool]
    is_creatures: list[bool]
    oracle_texts: list[str]
    matrix: np.ndarray  # shape (n, d), float32


def load_index(
    conn: duckdb.DuckDBPyConnection, model_alias: str
) -> EmbeddingIndex:
    """Load all embeddings for *model_alias* from DuckDB into an in-memory index."""
    from mtgdeck.embeddings.embed_cards import resolve_model_name

    model_id = resolve_model_name(model_alias)

    rows = conn.execute(
        """
        SELECT ce.normalized_name,
               c.name,
               c.type_line,
               c.color_identity,
               c.cmc,
               c.is_land,
               c.is_creature,
               c.oracle_text,
               ce.embedding
        FROM card_embeddings ce
        JOIN cards c ON c.normalized_name = ce.normalized_name
        WHERE ce.embedding_model = ?
        """,
        [model_id],
    ).fetchall()

    if not rows:
        return EmbeddingIndex(
            normalized_names=[],
            names=[],
            type_lines=[],
            color_identities=[],
            cmcs=[],
            is_lands=[],
            is_creatures=[],
            oracle_texts=[],
            matrix=np.empty((0, 0), dtype=np.float32),
        )

    normalized_names, names, type_lines, raw_cis, cmcs, is_lands, is_creatures, oracle_texts, embeddings = zip(
        *rows
    )

    color_identities = [
        json.loads(ci) if isinstance(ci, str) else (ci or [])
        for ci in raw_cis
    ]
    matrix = np.array(embeddings, dtype=np.float32)

    return EmbeddingIndex(
        normalized_names=list(normalized_names),
        names=list(names),
        type_lines=list(type_lines),
        color_identities=color_identities,
        cmcs=list(cmcs),
        is_lands=list(is_lands),
        is_creatures=list(is_creatures),
        oracle_texts=[t or "" for t in oracle_texts],
        matrix=matrix,
    )


def build_commander_query(
    commander_name: str,
    oracle_text: str,
    themes: list[str] | None = None,
    needed_roles: list[str] | None = None,
) -> str:
    """Build a semantic search query string from a commander's profile."""
    parts = [
        f"Commander: {commander_name}",
        f"Oracle Text: {oracle_text}",
    ]
    if themes:
        parts.append(f"Themes: {', '.join(themes)}")
    if needed_roles:
        parts.append(f"Needed roles: {', '.join(needed_roles)}")
    return "\n".join(parts)


def build_role_query(role: str, color_identity: list[str] | None = None) -> str:
    """Build a role-focused semantic search query."""
    parts = [f"Find cards that provide: {role}"]
    if color_identity:
        parts.append(f"Color identity: {'/'.join(color_identity)}")
    return "\n".join(parts)


def search(
    index: EmbeddingIndex,
    query_embedding: np.ndarray,
    *,
    commander_ci: list[str] | None = None,
    exclude_names: set[str] | None = None,
    top_k: int = 50,
    min_score: float = -1.0,
    lands_only: bool = False,
    exclude_lands: bool = False,
) -> list[SearchResult]:
    """Run a vector search over the index.

    Args:
        index: pre-loaded EmbeddingIndex.
        query_embedding: 1-D numpy array produced by the same model.
        commander_ci: if set, filters to cards within this color identity.
        exclude_names: card names already in the deck (skip them).
        top_k: maximum results to return.
        min_score: minimum cosine similarity threshold.
        lands_only: keep only land cards.
        exclude_lands: drop all land cards.

    Returns:
        List of SearchResult sorted by similarity_score descending.
    """
    from mtgdeck.rules.color_identity import is_within_color_identity

    if index.matrix.shape[0] == 0:
        return []

    scores: np.ndarray = cosine_similarity_batch(query_embedding, index.matrix)
    order = np.argsort(scores)[::-1]

    results: list[SearchResult] = []
    for idx in order:
        if len(results) >= top_k:
            break

        score = float(scores[idx])
        if score < min_score:
            break

        name = index.names[idx]
        norm_name = index.normalized_names[idx]
        ci = index.color_identities[idx]
        is_land = bool(index.is_lands[idx])

        if exclude_names and name in exclude_names:
            continue
        if commander_ci is not None and not is_within_color_identity(ci, commander_ci):
            continue
        if lands_only and not is_land:
            continue
        if exclude_lands and is_land:
            continue

        results.append(
            SearchResult(
                normalized_name=norm_name,
                name=name,
                type_line=index.type_lines[idx],
                color_identity=ci,
                cmc=float(index.cmcs[idx]),
                is_land=is_land,
                is_creature=bool(index.is_creatures[idx]),
                oracle_text=index.oracle_texts[idx],
                similarity_score=score,
            )
        )

    # Normalize scores within the result set
    if results:
        raw = np.array([r.similarity_score for r in results], dtype=np.float32)
        lo, hi = raw.min(), raw.max()
        span = hi - lo
        for i, r in enumerate(results):
            r.similarity_score_norm = float((raw[i] - lo) / span) if span > 0 else 1.0

    return results


def embed_and_search(
    conn: duckdb.DuckDBPyConnection,
    query_text: str,
    model_alias: str,
    *,
    commander_ci: list[str] | None = None,
    exclude_names: set[str] | None = None,
    top_k: int = 50,
    min_score: float = -1.0,
    exclude_lands: bool = False,
    lands_only: bool = False,
) -> list[SearchResult]:
    """Convenience wrapper: embed query text, load index, run search."""
    from mtgdeck.embeddings.embed_cards import load_model, resolve_model_name

    model = load_model(model_alias)
    query_vec: np.ndarray = model.encode(
        [query_text], show_progress_bar=False, convert_to_numpy=True
    )[0].astype(np.float32)

    index = load_index(conn, model_alias)
    return search(
        index,
        query_vec,
        commander_ci=commander_ci,
        exclude_names=exclude_names,
        top_k=top_k,
        min_score=min_score,
        exclude_lands=exclude_lands,
        lands_only=lands_only,
    )
