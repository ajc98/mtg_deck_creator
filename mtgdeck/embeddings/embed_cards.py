from __future__ import annotations

import json
from typing import TYPE_CHECKING

import duckdb
import numpy as np
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)

if TYPE_CHECKING:
    pass

# Model aliases → HuggingFace model IDs
MODEL_ALIASES: dict[str, str] = {
    "local": "all-MiniLM-L6-v2",         # 384 dims, fast, ~90 MB
    "local-large": "all-mpnet-base-v2",   # 768 dims, better quality, ~420 MB
}

MODEL_DEFAULT = "local"

_BATCH_SIZE = 256
_model_cache: dict[str, object] = {}


# ---------------------------------------------------------------------------
# Search-text builder
# ---------------------------------------------------------------------------


def build_card_search_text(card: dict) -> str:
    """Build the searchable text string for a card DB row."""
    lines: list[str] = [
        f"Name: {card['name']}",
        f"Type: {card['type_line'] or ''}",
        f"Mana Cost: {card['mana_cost'] or 'none'}",
        f"Mana Value: {int(card['cmc'] or 0)}",
        f"Oracle Text: {card['oracle_text'] or ''}",
    ]

    raw_kw = card.get("keywords")
    if raw_kw:
        kws: list[str] = json.loads(raw_kw) if isinstance(raw_kw, str) else raw_kw
        if kws:
            lines.append(f"Keywords: {', '.join(kws)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------


def resolve_model_name(alias_or_id: str) -> str:
    return MODEL_ALIASES.get(alias_or_id, alias_or_id)


def load_model(model_alias: str):
    """Load a SentenceTransformer model, caching it for the process lifetime."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is not installed.\n"
            "Install with:  pip install 'mtgdeck[embed]'"
        ) from exc

    model_id = resolve_model_name(model_alias)
    if model_id not in _model_cache:
        _model_cache[model_id] = SentenceTransformer(model_id)
    return _model_cache[model_id]


# ---------------------------------------------------------------------------
# Main embed pipeline
# ---------------------------------------------------------------------------


def embed_cards(
    conn: duckdb.DuckDBPyConnection,
    model_alias: str = MODEL_DEFAULT,
    batch_size: int = _BATCH_SIZE,
    force: bool = False,
) -> tuple[int, int]:
    """Embed all un-embedded cards and store in DuckDB.

    Returns (embedded, skipped).
    With force=True all existing embeddings for this model are cleared first.
    """
    from mtgdeck.data.duckdb_repo import (
        clear_embeddings,
        embedding_count,
        get_cards_without_embeddings,
        save_embeddings_batch,
    )

    model_id = resolve_model_name(model_alias)

    if force:
        clear_embeddings(conn, model_id)

    pending = get_cards_without_embeddings(conn, model_id)
    if not pending:
        already = embedding_count(conn, model_id)
        return 0, already

    model = load_model(model_alias)

    embedded = 0
    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task(
            f"Embedding with [bold]{model_id}[/bold]…", total=len(pending)
        )

        for offset in range(0, len(pending), batch_size):
            chunk = pending[offset : offset + batch_size]
            texts = [build_card_search_text(c) for c in chunk]

            vecs: np.ndarray = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

            rows = [
                (
                    chunk[i]["normalized_name"],
                    model_id,
                    vecs[i].astype(np.float64).tolist(),
                    texts[i],
                )
                for i in range(len(chunk))
            ]
            save_embeddings_batch(conn, rows)
            embedded += len(chunk)
            progress.advance(task, len(chunk))

    return embedded, 0
