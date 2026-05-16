from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import duckdb
from pydantic import ValidationError
from rich.progress import Progress, SpinnerColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.console import Console as _Console

from mtgdeck.data.duckdb_repo import insert_cards_batch
from mtgdeck.models import ScryfallCard

# Layouts that split card text across faces; top-level oracle_text may be empty
_MULTI_FACE_LAYOUTS = {
    "transform",
    "modal_dfc",
    "double_faced_token",
    "art_series",
    "reversible_card",
}

# Layouts to skip entirely (tokens are not real cards)
_SKIP_LAYOUTS = {"token", "emblem", "planar", "scheme", "vanguard"}

_BATCH_SIZE = 500


def _merge_oracle_text(raw: dict) -> str:
    """Return oracle text, merging card faces for multi-faced cards."""
    if raw.get("oracle_text"):
        return raw["oracle_text"]
    faces = raw.get("card_faces") or []
    return " // ".join(f.get("oracle_text", "") for f in faces if f.get("oracle_text"))


def _to_row(card: ScryfallCard, raw_json: str) -> tuple:
    return (
        card.oracle_id,
        card.id,
        card.name,
        card.normalized_name,
        card.type_line,
        card.full_oracle_text(),
        card.mana_cost,
        card.cmc,
        json.dumps(card.colors),
        json.dumps(card.color_identity),
        json.dumps(card.keywords),
        card.commander_legal,
        card.layout,
        card.is_basic_land,
        card.is_land,
        card.is_creature,
        card.is_artifact,
        card.is_enchantment,
        card.is_instant,
        card.is_sorcery,
        card.is_planeswalker,
        json.dumps(card.produced_mana) if card.produced_mana is not None else None,
        card.edhrec_rank,
        raw_json,
    )


def _iter_raw_cards(path: Path) -> Iterator[dict]:
    """Stream cards from a Scryfall Oracle JSON array without loading the whole file."""
    # Scryfall bulk files are JSON arrays; load fully for simplicity in phase 1.
    # The file is ~150 MB — fast enough with stdlib json.
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}, got {type(data).__name__}")
    yield from data


def ingest_scryfall(
    conn: duckdb.DuckDBPyConnection,
    path: Path,
) -> tuple[int, int, int]:
    """Ingest Scryfall Oracle JSON into DuckDB.

    Returns (inserted, skipped_layout, parse_errors).
    """
    inserted = 0
    skipped_layout = 0
    parse_errors = 0
    batch: list[tuple] = []

    def flush() -> None:
        nonlocal inserted
        if batch:
            insert_cards_batch(conn, batch)
            inserted += len(batch)
            batch.clear()

    _console = _Console(highlight=False)
    with Progress(
        SpinnerColumn(spinner_name="line"),  # ASCII-safe spinner
        "[progress.description]{task.description}",
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=_console,
    ) as progress:
        task = progress.add_task("Ingesting Scryfall cards…", total=None)

        for raw in _iter_raw_cards(path):
            layout = raw.get("layout", "")
            if layout in _SKIP_LAYOUTS:
                skipped_layout += 1
                continue

            # Ensure oracle_id exists; some promos/tokens may lack it
            if not raw.get("oracle_id"):
                skipped_layout += 1
                continue

            # Patch oracle_text for multi-face cards before parsing
            if not raw.get("oracle_text"):
                raw = {**raw, "oracle_text": _merge_oracle_text(raw)}

            try:
                card = ScryfallCard.model_validate(raw)
            except ValidationError:
                parse_errors += 1
                continue

            raw_json = json.dumps(raw, ensure_ascii=False)
            batch.append(_to_row(card, raw_json))

            if len(batch) >= _BATCH_SIZE:
                flush()

            progress.advance(task)

        flush()

    return inserted, skipped_layout, parse_errors
