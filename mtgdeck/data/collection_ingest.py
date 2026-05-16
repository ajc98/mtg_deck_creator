"""Ingest owned-card collections from CSV exports (Moxfield, etc.)."""
from __future__ import annotations

import csv
from pathlib import Path

import duckdb

from mtgdeck.models import normalize_name

# Column aliases across different export formats
_COUNT_COLS  = ("count", "quantity", "qty", "#")
_NAME_COLS   = ("name", "card name", "cardname")
_SET_COLS    = ("edition", "set", "set_code", "printing")
_CN_COLS     = ("collector number", "collector_number", "cn")
_FOIL_COLS   = ("foil",)


def _find_col(header: list[str], aliases: tuple[str, ...]) -> int | None:
    lower = [h.lower().strip() for h in header]
    for alias in aliases:
        if alias in lower:
            return lower.index(alias)
    return None


def ingest_collection(
    conn: duckdb.DuckDBPyConnection,
    path: Path,
    source: str = "moxfield",
    replace: bool = False,
) -> tuple[int, int]:
    """Import a CSV collection export into the *collection* table.

    Returns (inserted, skipped).
    replace=True clears existing rows for *source* before inserting.
    """
    if replace:
        conn.execute("DELETE FROM collection WHERE source = ?", [source])

    rows_inserted = 0
    rows_skipped = 0

    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = next(reader)

        count_idx = _find_col(header, _COUNT_COLS)
        name_idx  = _find_col(header, _NAME_COLS)
        set_idx   = _find_col(header, _SET_COLS)
        cn_idx    = _find_col(header, _CN_COLS)
        foil_idx  = _find_col(header, _FOIL_COLS)

        if name_idx is None:
            raise ValueError(
                f"Could not find name column in {path}. "
                f"Header: {header}"
            )

        for row in reader:
            if not row:
                continue

            raw_name = row[name_idx].strip()
            if not raw_name:
                rows_skipped += 1
                continue

            quantity = 1
            if count_idx is not None and row[count_idx].strip().isdigit():
                quantity = int(row[count_idx].strip())

            set_code = row[set_idx].strip() if set_idx is not None and set_idx < len(row) else ""
            cn       = row[cn_idx].strip()  if cn_idx  is not None and cn_idx  < len(row) else ""
            foil_raw = row[foil_idx].strip().lower() if foil_idx is not None and foil_idx < len(row) else "no"
            foil     = foil_raw in ("yes", "true", "1", "foil")

            norm = normalize_name(raw_name)

            conn.execute(
                """
                INSERT INTO collection (normalized_name, name, quantity, set_code, collector_number, foil, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (normalized_name) DO UPDATE SET
                    quantity         = collection.quantity + EXCLUDED.quantity,
                    set_code         = EXCLUDED.set_code,
                    collector_number = EXCLUDED.collector_number,
                    foil             = EXCLUDED.foil,
                    source           = EXCLUDED.source
                """,
                [norm, raw_name, quantity, set_code, cn, foil, source],
            )
            rows_inserted += 1

    return rows_inserted, rows_skipped
