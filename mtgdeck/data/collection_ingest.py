"""Ingest owned-card collections from CSV exports (Moxfield, etc.)."""
from __future__ import annotations

import csv
import tempfile
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
    Parses all rows into memory first then does a single bulk executemany.
    """
    if replace:
        # Wipe all rows so the bulk INSERT below needs no conflict check
        conn.execute("DELETE FROM collection")

    batch: list[tuple] = []
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
            if count_idx is not None and count_idx < len(row) and row[count_idx].strip().isdigit():
                quantity = int(row[count_idx].strip())

            set_code = row[set_idx].strip() if set_idx is not None and set_idx < len(row) else ""
            cn       = row[cn_idx].strip()  if cn_idx  is not None and cn_idx  < len(row) else ""
            foil_raw = row[foil_idx].strip().lower() if foil_idx is not None and foil_idx < len(row) else "no"
            foil     = foil_raw in ("yes", "true", "1", "foil")

            batch.append((normalize_name(raw_name), raw_name, quantity, set_code, cn, foil, source))

    if not batch:
        return 0, rows_skipped

    # Deduplicate within the CSV (same card listed multiple times → sum quantities)
    merged: dict[str, list] = {}
    for row in batch:
        norm = row[0]
        if norm in merged:
            merged[norm][2] += row[2]   # accumulate quantity
        else:
            merged[norm] = list(row)
    deduped = [tuple(r) for r in merged.values()]

    # Write processed rows to a temp CSV then load via DuckDB's vectorised
    # read_csv bulk-loader.  This is ~600× faster than row-by-row executemany.
    tmp_csv: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
        ) as fh:
            writer = csv.writer(fh)
            writer.writerow(["normalized_name", "name", "quantity", "set_code",
                              "collector_number", "foil", "source"])
            writer.writerows(deduped)
            tmp_csv = Path(fh.name)

        safe_path = str(tmp_csv).replace("\\", "/")
        conn.execute(f"""
            INSERT INTO collection
                (normalized_name, name, quantity, set_code, collector_number, foil, source)
            SELECT * FROM read_csv(
                '{safe_path}',
                header = true,
                columns = {{
                    'normalized_name': 'VARCHAR',
                    'name':            'VARCHAR',
                    'quantity':        'INTEGER',
                    'set_code':        'VARCHAR',
                    'collector_number':'VARCHAR',
                    'foil':            'BOOLEAN',
                    'source':          'VARCHAR'
                }}
            )
        """
        )
    finally:
        if tmp_csv and tmp_csv.exists():
            tmp_csv.unlink()

    return len(deduped), rows_skipped
