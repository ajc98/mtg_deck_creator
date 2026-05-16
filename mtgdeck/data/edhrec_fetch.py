from __future__ import annotations

import random
import time
from datetime import datetime, timedelta, timezone

import duckdb
import httpx

from mtgdeck.data.edhrec_parse import parse_edhrec_json, slugify

EDHREC_JSON_BASE = "https://json.edhrec.com/pages/commanders"

# How long cached data stays fresh before we re-fetch
CACHE_TTL_DAYS = 7

_HEADERS = {
    "User-Agent": (
        "mtgdeck-cli/0.1 (personal commander deck builder; "
        "https://github.com/ajc98/mtg_deck_creator)"
    ),
    "Accept": "application/json",
}

# Polite delay range between requests
_DELAY_MIN = 1.5
_DELAY_MAX = 3.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_fresh(fetched_at: datetime, ttl_days: int = CACHE_TTL_DAYS) -> bool:
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    age = datetime.now(tz=timezone.utc) - fetched_at
    return age < timedelta(days=ttl_days)


def _polite_delay() -> None:
    time.sleep(random.uniform(_DELAY_MIN, _DELAY_MAX))


def _fetch_url(url: str, max_retries: int = 3) -> httpx.Response:
    """GET url with exponential back-off on 429 and transient network errors."""
    backoff = 2.0
    last_exc: Exception | None = None

    for attempt in range(max_retries):
        try:
            with httpx.Client(
                headers=_HEADERS, timeout=30, follow_redirects=True
            ) as client:
                resp = client.get(url)

            if resp.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                resp.raise_for_status()

            resp.raise_for_status()
            return resp

        except httpx.HTTPStatusError:
            raise
        except httpx.RequestError as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(backoff)
                backoff *= 2

    raise RuntimeError(
        f"Network error after {max_retries} attempts for {url}: {last_exc}"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_edhrec(
    conn: duckdb.DuckDBPyConnection,
    commander_name: str,
    *,
    force: bool = False,
    ttl_days: int = CACHE_TTL_DAYS,
) -> dict:
    """Fetch and cache EDHREC recommendations for *commander_name*.

    Returns a dict with keys:
        from_cache   bool
        fetched_at   datetime
        slug         str
        url          str
        card_count   int  (number of recommendation records)
        records      list[dict]

    Uses cached data when fresh (< ttl_days old) unless force=True.
    """
    from mtgdeck.data.duckdb_repo import (
        get_edhrec_page,
        get_edhrec_recommendations,
        save_edhrec_page,
        save_edhrec_recommendations,
    )

    # --- Cache hit ---
    if not force:
        cached_page = get_edhrec_page(conn, commander_name)
        if cached_page and cached_page.get("raw_json") and _is_fresh(
            cached_page["fetched_at"], ttl_days
        ):
            recs = get_edhrec_recommendations(conn, commander_name)
            return {
                "from_cache": True,
                "fetched_at": cached_page["fetched_at"],
                "slug": cached_page["commander_slug"],
                "url": cached_page["url"],
                "card_count": len(recs),
                "records": recs,
            }

    # --- Cache miss: fetch ---
    slug = slugify(commander_name)
    url = f"{EDHREC_JSON_BASE}/{slug}.json"

    _polite_delay()

    try:
        resp = _fetch_url(url)
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 404:
            raise LookupError(
                f"Commander '{commander_name}' (slug: {slug}) not found on EDHREC. "
                "Check spelling or try the exact EDHREC name."
            ) from exc
        raise RuntimeError(
            f"EDHREC returned HTTP {status} for {url}"
        ) from exc

    raw_json_text = resp.text
    data = resp.json()

    records = parse_edhrec_json(data, commander_name, url)
    now = datetime.now(tz=timezone.utc)

    save_edhrec_page(
        conn,
        {
            "commander_name": commander_name,
            "commander_slug": slug,
            "url": url,
            "fetched_at": now,
            "raw_html": None,
            "raw_json": raw_json_text,
        },
    )
    save_edhrec_recommendations(conn, commander_name, records, now)

    return {
        "from_cache": False,
        "fetched_at": now,
        "slug": slug,
        "url": url,
        "card_count": len(records),
        "records": records,
    }
