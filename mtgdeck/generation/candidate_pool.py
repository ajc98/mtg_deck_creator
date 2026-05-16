"""Build the scored candidate pool for deck construction."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import duckdb

from mtgdeck.rules.color_identity import is_within_color_identity
from mtgdeck.rules.commander_rules import CommanderProfile
from mtgdeck.scoring.role_classifier import classify_card

# SQL conditions for mandatory-role DB queries (approximate; Python re-checks roles)
_ROLE_SQL: dict[str, str] = {
    "land":       "is_land = TRUE",
    "mana_rock":  "is_artifact = TRUE AND is_creature = FALSE AND oracle_text LIKE '%add {%'",
    "mana_dork":  "is_creature = TRUE AND oracle_text LIKE '%add {%'",
    "land_ramp":  "oracle_text LIKE '%search your library for%land%'",
    "card_draw":  "oracle_text LIKE '%draw % card%' OR oracle_text LIKE '%draw a card%'",
    "removal":    "(oracle_text LIKE '%destroy target%' OR oracle_text LIKE '%exile target%')",
    "board_wipe": "(oracle_text LIKE '%destroy all%' OR oracle_text LIKE '%exile all%')",
    "counterspell": "oracle_text LIKE '%counter target spell%'",
    "recursion":  "oracle_text LIKE '%from%graveyard%'",
}
_MANDATORY_MIN = 25   # candidates per role before we hit the DB
_DB_FETCH_LIMIT = 120


@dataclass
class CandidateCard:
    normalized_name: str
    name: str
    card_row: dict
    edhrec_rec: dict | None
    vector_score: float
    roles: list[str] = field(default_factory=list)


def _row_color_identity(row: dict) -> list[str]:
    raw = row.get("color_identity") or "[]"
    return json.loads(raw) if isinstance(raw, str) else list(raw)


def build_candidate_pool(
    conn: duckdb.DuckDBPyConnection,
    profile: CommanderProfile,
    edhrec_recs: list[dict],
    *,
    embedding_index=None,   # EmbeddingIndex | None
    model_alias: str = "local",
    owned_names: set[str] | None = None,
    owned_only: bool = False,
) -> list[CandidateCard]:
    """Assemble a deduplicated, colour-identity-filtered candidate pool.

    Sources (in order):
    1. EDHREC recommendations (primary signal)
    2. Vector search results per role query (if embeddings are loaded)
    3. DB queries for mandatory roles that are under-represented
    """
    from mtgdeck.data.duckdb_repo import get_card_by_normalized_name, get_candidates_by_sql

    commander_ci   = profile.color_identity
    commander_name = profile.card.name
    edhrec_map     = {r["normalized_card_name"]: r for r in edhrec_recs}

    pool: dict[str, CandidateCard] = {}

    # ── 1. EDHREC recommendations ────────────────────────────────────────────
    for rec in edhrec_recs:
        norm = rec["normalized_card_name"]
        if norm == profile.card.normalized_name:
            continue
        row = get_card_by_normalized_name(conn, norm)
        if row is None or not row.get("legal_commander"):
            continue
        if not is_within_color_identity(_row_color_identity(row), commander_ci):
            continue
        pool[norm] = CandidateCard(
            normalized_name=norm,
            name=row["name"],
            card_row=row,
            edhrec_rec=rec,
            vector_score=0.0,
            roles=classify_card(row),
        )

    # ── 2. Vector search ─────────────────────────────────────────────────────
    if embedding_index is not None and embedding_index.matrix.shape[0] > 0:
        _add_vector_candidates(
            pool, conn, profile, embedding_index, model_alias,
            edhrec_map, commander_ci
        )

    # ── 3. DB fill for under-represented mandatory roles ─────────────────────
    for role, sql in _ROLE_SQL.items():
        count_with_role = sum(1 for c in pool.values() if role in c.roles)
        if count_with_role >= _MANDATORY_MIN:
            continue
        rows = get_candidates_by_sql(conn, sql, limit=_DB_FETCH_LIMIT)
        for row in rows:
            norm = row["normalized_name"]
            if norm in pool or norm == profile.card.normalized_name:
                continue
            if not row.get("legal_commander"):
                continue
            if not is_within_color_identity(_row_color_identity(row), commander_ci):
                continue
            pool[norm] = CandidateCard(
                normalized_name=norm,
                name=row["name"],
                card_row=row,
                edhrec_rec=edhrec_map.get(norm),
                vector_score=0.0,
                roles=classify_card(row),
            )

    # ── 4. Owned-only filter ─────────────────────────────────────────────────
    if owned_only and owned_names:
        pool = {k: v for k, v in pool.items() if v.name in owned_names}

    return list(pool.values())


def _add_vector_candidates(
    pool: dict[str, CandidateCard],
    conn: duckdb.DuckDBPyConnection,
    profile: CommanderProfile,
    embedding_index,
    model_alias: str,
    edhrec_map: dict[str, dict],
    commander_ci: list[str],
) -> None:
    from mtgdeck.data.duckdb_repo import get_card_by_normalized_name
    from mtgdeck.embeddings.embed_cards import load_model
    from mtgdeck.embeddings.vector_search import build_commander_query, build_role_query, search

    import numpy as np

    try:
        model = load_model(model_alias)
    except RuntimeError:
        return  # embeddings not installed — skip gracefully

    queries = [
        build_commander_query(
            profile.card.name,
            profile.card.full_oracle_text(),
        ),
        build_role_query("ramp mana rocks artifacts"),
        build_role_query("card draw card advantage"),
        build_role_query("removal interaction destroy exile"),
        build_role_query("board wipe mass removal sweeper"),
        build_role_query("win condition finisher combo"),
        build_role_query("protection hexproof indestructible"),
        build_role_query("lands utility land"),
    ]

    for query_text in queries:
        vec: np.ndarray = model.encode(
            [query_text], show_progress_bar=False, convert_to_numpy=True
        )[0].astype(np.float32)

        results = search(
            embedding_index,
            vec,
            commander_ci=commander_ci,
            exclude_names={profile.card.name},
            top_k=40,
        )

        for r in results:
            norm = r.normalized_name
            if norm in pool:
                # Upgrade vector score if this query gave a better match
                if r.similarity_score_norm > pool[norm].vector_score:
                    pool[norm].vector_score = r.similarity_score_norm
                continue

            row = get_card_by_normalized_name(conn, norm)
            if row is None or not row.get("legal_commander"):
                continue

            pool[norm] = CandidateCard(
                normalized_name=norm,
                name=r.name,
                card_row=row,
                edhrec_rec=edhrec_map.get(norm),
                vector_score=r.similarity_score_norm,
                roles=classify_card(row),
            )
