"""
Check which commanders have EDHREC data and which don't.
Writes two files:
  - edhrec_ok.txt       — commanders with data (rank + decks)
  - edhrec_missing.txt  — commanders with no EDHREC page
"""
from __future__ import annotations

import io
import json
import re
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

# Force UTF-8 stdout so special card name characters don't crash on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))
from mtgdeck.data.duckdb_repo import get_connection


def edhrec_slug(name: str) -> str:
    name = name.split(" // ")[0]
    name = name.lower().replace("-", " ")
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^a-z0-9 ]", "", name)
    return re.sub(r"\s+", "-", name.strip())


def fetch_edhrec(slug: str) -> dict | None:
    url = f"https://json.edhrec.com/pages/commanders/{slug}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "MTGDeckCreator/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        card = data.get("container", {}).get("json_dict", {}).get("card", {})
        return {
            "rank": card.get("rank"),
            "num_decks": card.get("num_decks", 0),
        }
    except Exception:
        return None


def main() -> None:
    conn = get_connection()
    rows = conn.execute("""
        SELECT name FROM cards
        WHERE legal_commander = TRUE
          AND (type_line LIKE 'Legendary Creature%'
               OR (type_line LIKE 'Legendary Planeswalker%'
                   AND lower(oracle_text) LIKE '%can be your commander%'))
        ORDER BY name
    """).fetchall()

    commanders = [r[0] for r in rows]
    total = len(commanders)
    print(f"Checking {total} commanders against EDHREC…")

    ok: list[tuple[str, int, int]] = []     # (name, rank, num_decks)
    missing: list[str] = []

    for i, name in enumerate(commanders, 1):
        slug = edhrec_slug(name)
        result = fetch_edhrec(slug)

        if result and result.get("num_decks", 0) > 0:
            ok.append((name, result["rank"] or 0, result["num_decks"]))
            status = f"#{result['rank']}  {result['num_decks']:,} decks"
        else:
            missing.append(name)
            status = "NOT FOUND"

        print(f"  [{i:4}/{total}]  {status:<30}  {name}")
        time.sleep(0.15)   # ~6-7 req/s — polite to EDHREC

    out_dir = Path(__file__).parent
    ok_path = out_dir / "edhrec_ok.txt"
    missing_path = out_dir / "edhrec_missing.txt"

    ok_path.write_text(
        "\n".join(f"#{rank:<6} {decks:>6} decks  {name}" for name, rank, decks in ok),
        encoding="utf-8",
    )
    missing_path.write_text("\n".join(missing), encoding="utf-8")

    print(f"\nDone.")
    print(f"  Have EDHREC data : {len(ok)}")
    print(f"  Missing          : {len(missing)}")
    print(f"  Results saved to : {ok_path}")
    print(f"                     {missing_path}")


if __name__ == "__main__":
    main()
