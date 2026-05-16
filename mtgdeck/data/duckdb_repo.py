from __future__ import annotations

import duckdb

from mtgdeck.config import DB_PATH, ensure_data_dir

_DDL = [
    """
    CREATE TABLE IF NOT EXISTS cards (
        oracle_id        TEXT PRIMARY KEY,
        scryfall_id      TEXT,
        name             TEXT NOT NULL,
        normalized_name  TEXT NOT NULL,
        type_line        TEXT,
        oracle_text      TEXT,
        mana_cost        TEXT,
        cmc              DOUBLE,
        colors           TEXT,
        color_identity   TEXT,
        keywords         TEXT,
        legal_commander  BOOLEAN,
        layout           TEXT,
        is_basic_land    BOOLEAN,
        is_land          BOOLEAN,
        is_creature      BOOLEAN,
        is_artifact      BOOLEAN,
        is_enchantment   BOOLEAN,
        is_instant       BOOLEAN,
        is_sorcery       BOOLEAN,
        is_planeswalker  BOOLEAN,
        produced_mana    TEXT,
        edhrec_rank      INTEGER,
        raw_json         TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS collection (
        normalized_name  TEXT PRIMARY KEY,
        name             TEXT,
        quantity         INTEGER,
        set_code         TEXT,
        collector_number TEXT,
        foil             BOOLEAN,
        source           TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS card_embeddings (
        normalized_name  TEXT,
        embedding_model  TEXT,
        embedding        DOUBLE[],
        embedded_text    TEXT,
        created_at       TIMESTAMP,
        PRIMARY KEY (normalized_name, embedding_model)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS edhrec_pages (
        commander_name   TEXT PRIMARY KEY,
        commander_slug   TEXT,
        url              TEXT,
        fetched_at       TIMESTAMP,
        raw_html         TEXT,
        raw_json         TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS edhrec_recommendations (
        commander_name       TEXT,
        card_name            TEXT,
        normalized_card_name TEXT,
        section              TEXT,
        theme                TEXT,
        synergy_score        DOUBLE,
        deck_percentage      DOUBLE,
        deck_count           INTEGER,
        salt_score           DOUBLE,
        source_url           TEXT,
        fetched_at           TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS generated_decks (
        deck_id        TEXT PRIMARY KEY,
        commander_name TEXT,
        created_at     TIMESTAMP,
        config_json    TEXT,
        deck_json      TEXT,
        decklist_text  TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS card_scores (
        deck_id                  TEXT,
        card_name                TEXT,
        role                     TEXT,
        final_score              DOUBLE,
        edhrec_score             DOUBLE,
        vector_similarity_score  DOUBLE,
        role_need_score          DOUBLE,
        commander_synergy_score  DOUBLE,
        mana_curve_score         DOUBLE,
        collection_score         DOUBLE,
        budget_score             DOUBLE,
        explanation              TEXT
    )
    """,
]

_INSERT_CARD = """
INSERT INTO cards (
    oracle_id, scryfall_id, name, normalized_name, type_line, oracle_text,
    mana_cost, cmc, colors, color_identity, keywords, legal_commander,
    layout, is_basic_land, is_land, is_creature, is_artifact, is_enchantment,
    is_instant, is_sorcery, is_planeswalker, produced_mana, edhrec_rank, raw_json
) VALUES (
    ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?
)
ON CONFLICT (oracle_id) DO UPDATE SET
    scryfall_id     = EXCLUDED.scryfall_id,
    name            = EXCLUDED.name,
    normalized_name = EXCLUDED.normalized_name,
    type_line       = EXCLUDED.type_line,
    oracle_text     = EXCLUDED.oracle_text,
    mana_cost       = EXCLUDED.mana_cost,
    cmc             = EXCLUDED.cmc,
    colors          = EXCLUDED.colors,
    color_identity  = EXCLUDED.color_identity,
    keywords        = EXCLUDED.keywords,
    legal_commander = EXCLUDED.legal_commander,
    layout          = EXCLUDED.layout,
    is_basic_land   = EXCLUDED.is_basic_land,
    is_land         = EXCLUDED.is_land,
    is_creature     = EXCLUDED.is_creature,
    is_artifact     = EXCLUDED.is_artifact,
    is_enchantment  = EXCLUDED.is_enchantment,
    is_instant      = EXCLUDED.is_instant,
    is_sorcery      = EXCLUDED.is_sorcery,
    is_planeswalker = EXCLUDED.is_planeswalker,
    produced_mana   = EXCLUDED.produced_mana,
    edhrec_rank     = EXCLUDED.edhrec_rank,
    raw_json        = EXCLUDED.raw_json
"""


def get_connection() -> duckdb.DuckDBPyConnection:
    ensure_data_dir()
    conn = duckdb.connect(str(DB_PATH))
    for stmt in _DDL:
        conn.execute(stmt)
    return conn


def card_count(conn: duckdb.DuckDBPyConnection) -> int:
    return conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]


def lookup_card_by_name(
    conn: duckdb.DuckDBPyConnection, name: str
) -> dict | None:
    from mtgdeck.models import normalize_name

    row = conn.execute(
        "SELECT * FROM cards WHERE normalized_name = ? LIMIT 1",
        [normalize_name(name)],
    ).fetchone()
    if row is None:
        return None
    cols = [d[0] for d in conn.description]
    return dict(zip(cols, row))


def insert_cards_batch(
    conn: duckdb.DuckDBPyConnection, rows: list[tuple]
) -> int:
    conn.executemany(_INSERT_CARD, rows)
    return len(rows)


# ---------------------------------------------------------------------------
# EDHREC
# ---------------------------------------------------------------------------

_INSERT_EDHREC_PAGE = """
INSERT INTO edhrec_pages
    (commander_name, commander_slug, url, fetched_at, raw_html, raw_json)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT (commander_name) DO UPDATE SET
    commander_slug = EXCLUDED.commander_slug,
    url            = EXCLUDED.url,
    fetched_at     = EXCLUDED.fetched_at,
    raw_html       = EXCLUDED.raw_html,
    raw_json       = EXCLUDED.raw_json
"""

_INSERT_EDHREC_REC = """
INSERT INTO edhrec_recommendations
    (commander_name, card_name, normalized_card_name, section, theme,
     synergy_score, deck_percentage, deck_count, salt_score, source_url, fetched_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def get_edhrec_page(
    conn: duckdb.DuckDBPyConnection, commander_name: str
) -> dict | None:
    row = conn.execute(
        "SELECT * FROM edhrec_pages WHERE commander_name = ?", [commander_name]
    ).fetchone()
    if row is None:
        return None
    cols = [d[0] for d in conn.description]
    return dict(zip(cols, row))


def save_edhrec_page(
    conn: duckdb.DuckDBPyConnection, page: dict
) -> None:
    conn.execute(
        _INSERT_EDHREC_PAGE,
        [
            page["commander_name"],
            page["commander_slug"],
            page["url"],
            page["fetched_at"],
            page.get("raw_html"),
            page["raw_json"],
        ],
    )


def save_edhrec_recommendations(
    conn: duckdb.DuckDBPyConnection,
    commander_name: str,
    records: list[dict],
    fetched_at,
) -> None:
    conn.execute(
        "DELETE FROM edhrec_recommendations WHERE commander_name = ?",
        [commander_name],
    )
    rows = [
        (
            r["commander_name"],
            r["card_name"],
            r["normalized_card_name"],
            r["section"],
            r["theme"],
            r["synergy_score"],
            r["deck_percentage"],
            r["deck_count"],
            r["salt_score"],
            r["source_url"],
            fetched_at,
        )
        for r in records
    ]
    if rows:
        conn.executemany(_INSERT_EDHREC_REC, rows)


def get_edhrec_recommendations(
    conn: duckdb.DuckDBPyConnection,
    commander_name: str,
    section: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    sql = (
        "SELECT * FROM edhrec_recommendations WHERE commander_name = ?"
    )
    params: list = [commander_name]
    if section:
        sql += " AND section = ?"
        params.append(section)
    sql += " ORDER BY deck_percentage DESC"
    if limit:
        sql += f" LIMIT {limit}"

    rows = conn.execute(sql, params).fetchall()
    cols = [d[0] for d in conn.description]
    return [dict(zip(cols, row)) for row in rows]


def clear_edhrec_cache(
    conn: duckdb.DuckDBPyConnection, commander_name: str
) -> None:
    conn.execute(
        "DELETE FROM edhrec_pages WHERE commander_name = ?", [commander_name]
    )
    conn.execute(
        "DELETE FROM edhrec_recommendations WHERE commander_name = ?",
        [commander_name],
    )


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

_INSERT_EMBEDDING = """
INSERT INTO card_embeddings (normalized_name, embedding_model, embedding, embedded_text, created_at)
VALUES (?, ?, ?, ?, NOW())
ON CONFLICT (normalized_name, embedding_model) DO UPDATE SET
    embedding     = EXCLUDED.embedding,
    embedded_text = EXCLUDED.embedded_text,
    created_at    = EXCLUDED.created_at
"""


def get_cards_without_embeddings(
    conn: duckdb.DuckDBPyConnection, model_id: str
) -> list[dict]:
    """Return cards that have no embedding for *model_id* yet."""
    rows = conn.execute(
        """
        SELECT c.normalized_name, c.name, c.type_line, c.mana_cost,
               c.cmc, c.oracle_text, c.keywords
        FROM cards c
        LEFT JOIN card_embeddings ce
            ON ce.normalized_name = c.normalized_name
            AND ce.embedding_model = ?
        WHERE ce.normalized_name IS NULL
        ORDER BY c.name
        """,
        [model_id],
    ).fetchall()
    cols = [d[0] for d in conn.description]
    return [dict(zip(cols, row)) for row in rows]


def save_embeddings_batch(
    conn: duckdb.DuckDBPyConnection,
    rows: list[tuple],
) -> None:
    """rows: list of (normalized_name, model_id, embedding_list, embedded_text)."""
    conn.executemany(_INSERT_EMBEDDING, rows)


def embedding_count(conn: duckdb.DuckDBPyConnection, model_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM card_embeddings WHERE embedding_model = ?", [model_id]
    ).fetchone()[0]


def clear_embeddings(conn: duckdb.DuckDBPyConnection, model_id: str) -> None:
    conn.execute(
        "DELETE FROM card_embeddings WHERE embedding_model = ?", [model_id]
    )
