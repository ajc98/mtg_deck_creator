"""FastAPI backend for the MTG Commander Deck Creator UI."""
from __future__ import annotations

import asyncio
import json
import re
import sys
import tempfile
import threading
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

# Make the mtgdeck package importable from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from mtgdeck.data.duckdb_repo import get_connection

app = FastAPI(title="MTG Deck Creator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_DECKS_DIR = Path(__file__).parent.parent / "commanders_cleaned"


# ── Deck strategy generation ─────────────────────────────────────────────────

def _extract_commander_ability(oracle_lower: str) -> str:
    """Return a plain-English description of the commander's primary ability."""
    if "proliferate" in oracle_lower:
        if "end step" in oracle_lower:
            return "proliferates at the beginning of each end step, adding an extra counter to every permanent that already has one"
        return "has the proliferate ability, letting it grow counters on all your permanents on command"
    if "whenever a creature you control attacks" in oracle_lower:
        return "triggers a powerful effect whenever any of your creatures attacks"
    if ("whenever you cast" in oracle_lower and
            ("instant" in oracle_lower or "sorcery" in oracle_lower)):
        return "rewards you for casting instants and sorceries, turning each spell into extra value"
    if "whenever you cast" in oracle_lower:
        return "rewards you each time you cast a spell"
    if "whenever you draw" in oracle_lower:
        return "rewards card drawing, turning each draw into additional effects"
    if "whenever another creature dies" in oracle_lower or "whenever a creature dies" in oracle_lower:
        return "generates value whenever creatures die, making every combat and removal spell profitable"
    if "enters the battlefield" in oracle_lower and "whenever" in oracle_lower:
        return "benefits from creatures entering the battlefield under your control"
    if "sacrifice" in oracle_lower and "whenever" in oracle_lower:
        return "rewards sacrificing permanents, turning each sacrifice into advantage"
    if "token" in oracle_lower and ("create" in oracle_lower or "put" in oracle_lower):
        return "creates creature tokens, generating board presence over time"
    if "+1/+1 counter" in oracle_lower:
        return "interacts with +1/+1 counters, growing your creatures over time"
    kws = [kw for kw in ["flying", "deathtouch", "lifelink", "trample", "indestructible", "hexproof"] if kw in oracle_lower]
    if kws:
        return f"has {', '.join(kws[:3])}, making it a resilient threat on its own"
    return "has powerful abilities that reward building around them"


def _extract_synergy_keywords(oracle_lower: str) -> list[str]:
    """Return game-mechanics keywords that define the commander's strategy."""
    candidates = [
        "proliferate", "+1/+1 counter", "loyalty counter", "experience counter",
        "poison counter", "energy", "treasure", "token", "sacrifice", "dies",
        "graveyard", "draw a card", "whenever you draw", "attacks", "combat damage",
        "infect", "enchant", "equip", "return", "exile", "enters the battlefield",
    ]
    return [p for p in candidates if p in oracle_lower][:6]


def _build_strategy_guide(
    commander_name: str,
    commander_oracle: str,
    deck_cards: list[dict],
    archetypes: list[str],
) -> dict:
    """Analyse the actual 99 deck cards to produce a card-specific strategy guide."""
    from mtgdeck.scoring.role_classifier import (
        classify_card, RAMP_ROLES, DRAW_ROLES,
        ROLE_REMOVAL, ROLE_BOARD_WIPE, ROLE_WIN_CONDITION, ROLE_PROTECTION,
    )

    non_land = [c for c in deck_cards if not c.get("is_land")]
    lands     = [c for c in deck_cards if c.get("is_land") and not c.get("is_basic_land")]

    def role_names(roles: set, n: int = 4) -> list[str]:
        seen: list[str] = []
        for c in non_land:
            if any(r in roles for r in classify_card(c)):
                seen.append(c["name"])
                if len(seen) >= n:
                    break
        return seen

    ramp       = role_names(RAMP_ROLES, 5)
    draw       = role_names(DRAW_ROLES, 4)
    removal    = role_names({ROLE_REMOVAL}, 3)
    wipes      = role_names({ROLE_BOARD_WIPE}, 2)
    protection = role_names({ROLE_PROTECTION}, 2)
    wincons    = role_names({ROLE_WIN_CONDITION}, 4)
    creatures  = [c["name"] for c in non_land if c.get("is_creature")][:5]
    util_lands = [c["name"] for c in lands][:4]

    oracle_lower      = (commander_oracle or "").lower()
    ability_desc      = _extract_commander_ability(oracle_lower)
    synergy_keywords  = _extract_synergy_keywords(oracle_lower)

    # Find cards whose oracle text mentions the same keywords as the commander
    synergy_cards: list[str] = []
    for c in non_land:
        c_oracle = (c.get("oracle_text") or "").lower()
        if any(kw in c_oracle for kw in synergy_keywords) and c["name"] not in synergy_cards:
            synergy_cards.append(c["name"])
    synergy_cards = synergy_cards[:7]

    def _join(lst: list[str], n: int = 3) -> str:
        return ", ".join(lst[:n])

    # ── Gameplan ──────────────────────────────────────────────────────────────
    gp_parts = [f"{commander_name} {ability_desc}."]
    if synergy_cards:
        gp_parts.append(
            f"The deck's engine centres on {_join(synergy_cards, 3)}, "
            f"all of which interact directly with that ability each turn cycle."
        )
    if wincons:
        gp_parts.append(
            f"The primary paths to victory run through {_join(wincons, 2)}."
        )
    gameplan = " ".join(gp_parts)

    # ── Early game ────────────────────────────────────────────────────────────
    eg_parts = []
    if ramp:
        eg_parts.append(
            f"Your opening priority is mana acceleration — find {_join(ramp, 3)} "
            f"to hit your mana targets before casting {commander_name}."
        )
    if util_lands:
        eg_parts.append(
            f"Prioritise utility lands like {_join(util_lands, 2)} in your first "
            f"three land drops; they provide more than just mana."
        )
    eg_parts.append(
        f"Delay casting {commander_name} until you can follow up with at least one "
        f"synergy piece the same turn or immediately after."
    )
    early_game = " ".join(eg_parts)

    # ── Mid game ─────────────────────────────────────────────────────────────
    mg_parts = [f"Once {commander_name} is in play, chain your synergy cards together."]
    if synergy_cards:
        mg_parts.append(
            f"{synergy_cards[0]} is your highest-value combo piece — treat it as your "
            f"primary target for protection and your opponents' removal priority."
        )
    if draw:
        mg_parts.append(
            f"Keep cards flowing with {_join(draw, 2)} so you never run out of answers or threats."
        )
    if removal:
        mg_parts.append(
            f"Hold {_join(removal, 2)} for the most threatening permanents; "
            f"save interaction for things that stop your win condition."
        )
    mid_game = " ".join(mg_parts)

    # ── Late game ─────────────────────────────────────────────────────────────
    lg_parts = []
    if wincons:
        lg_parts.append(f"Your win-condition package: {_join(wincons, 4)}.")
    if protection:
        lg_parts.append(
            f"Shield your combo or key permanents with {_join(protection, 2)} — "
            f"opponents will try to stop you in this phase."
        )
    if wipes:
        lg_parts.append(
            f"If the board becomes unmanageable, {_join(wipes, 1)} resets it in your favour "
            f"since your engine recovers faster than opponents'."
        )
    if not lg_parts:
        lg_parts.append(
            "Your synergy cards should have built insurmountable advantage. "
            "Protect your board and close out the game."
        )
    late_game = " ".join(lg_parts)

    # ── Key actions ───────────────────────────────────────────────────────────
    key_actions: list[str] = []
    if synergy_cards:
        key_actions.append(
            f"Resolve {synergy_cards[0]} as early as possible — "
            f"it directly amplifies {commander_name}'s ability on every turn cycle."
        )
    if ramp:
        key_actions.append(
            f"Prioritise {ramp[0]} over any other play in your first three turns. "
            f"Early mana leads to every other advantage."
        )
    if wincons:
        key_actions.append(
            f"Cast {wincons[0]} only when you have mana to protect it or can go off "
            f"immediately — do not telegraph your win too early."
        )
    if creatures and len(creatures) > 1:
        key_actions.append(
            f"Keep at least one creature back as a blocker; your creatures "
            f"({creatures[0]}, {creatures[1]}…) also feed the engine."
        )
    key_actions = key_actions[:4]

    all_key = list(dict.fromkeys(synergy_cards[:3] + wincons[:2] + ramp[:1]))[:6]

    return {
        "gameplan":   gameplan,
        "early_game": early_game,
        "mid_game":   mid_game,
        "late_game":  late_game,
        "key_actions": key_actions,
        "key_cards":  all_key,
        "ramp":       ramp,
        "draw":       draw,
        "removal":    removal,
        "wipes":      wipes,
    }


# Module-level embedding index cache — loaded once, reused across builds
_index_lock: threading.Lock = threading.Lock()
_index_cache: dict = {}  # model_id -> EmbeddingIndex
_warmup_done: bool = False


@app.on_event("startup")
async def _startup_warmup() -> None:
    """Pre-load the embedding index in the background so the first build is fast."""
    async def _do_warmup() -> None:
        global _warmup_done
        try:
            def _load() -> None:
                from mtgdeck.data.duckdb_repo import (
                    get_connection as _gc, embedding_count as _ec
                )
                from mtgdeck.embeddings.embed_cards import resolve_model_name as _rmn
                from mtgdeck.embeddings.vector_search import load_index as _li
                _conn = _gc()
                _mid = _rmn("local")
                if _ec(_conn, _mid) > 0:
                    with _index_lock:
                        if _mid not in _index_cache:
                            _index_cache[_mid] = _li(_conn, _mid)
            await asyncio.to_thread(_load)
        except Exception as _exc:
            print(f"[warmup] Embedding warmup failed: {_exc}")
        finally:
            _warmup_done = True

    asyncio.create_task(_do_warmup())


def _deck_filename(commander_name: str) -> str:
    """Normalize a commander name to match the sanitized filenames on disk."""
    return re.sub(r"[/\\'\"]", "_", commander_name)


def _edhrec_slug(name: str) -> str:
    """Convert a commander name to an EDHREC URL slug.
    e.g. "K'rrik, Son of Yawgmoth"    -> "krrik-son-of-yawgmoth"
         "Kirol, Attentive First-Year" -> "kirol-attentive-first-year"
         "Éomer, King of Rohan"        -> "eomer-king-of-rohan"
    For double-faced cards, uses only the first face name.
    """
    name = name.split(" // ")[0]
    name = name.lower()
    name = name.replace("-", " ")                        # treat hyphens as word separators
    name = unicodedata.normalize("NFKD", name)           # decompose accented chars (é → e + combining)
    name = name.encode("ascii", "ignore").decode("ascii") # drop combining marks, keep base letters
    name = re.sub(r"[^a-z0-9 ]", "", name)              # strip remaining punctuation
    return re.sub(r"\s+", "-", name.strip())


def _color_names(color_identity: str | list) -> list[str]:
    mapping = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}
    if isinstance(color_identity, str):
        try:
            colors = json.loads(color_identity)
        except Exception:
            colors = []
    else:
        colors = list(color_identity or [])
    return [mapping.get(c, c) for c in colors]


def _color_symbols(color_identity: str | list) -> list[str]:
    if isinstance(color_identity, str):
        try:
            return json.loads(color_identity)
        except Exception:
            return []
    return list(color_identity or [])


@app.get("/api/commanders/search")
def search_commanders(q: str = Query(default="", min_length=0)):
    """Return all legal commanders (creatures + planeswalkers that allow it)."""
    conn = get_connection()
    base_where = """
        c.legal_commander = TRUE
        AND (
            c.type_line LIKE 'Legendary Creature%'
            OR (
                c.type_line LIKE 'Legendary Planeswalker%'
                AND lower(c.oracle_text) LIKE '%can be your commander%'
            )
        )
    """
    if not q.strip():
        rows = conn.execute(f"""
            SELECT c.name, c.color_identity, c.type_line,
                   (col.normalized_name IS NOT NULL) AS in_collection
            FROM cards c
            LEFT JOIN collection col ON col.normalized_name = c.normalized_name
            WHERE {base_where}
            ORDER BY c.name
        """).fetchall()
    else:
        like = f"%{q.lower()}%"
        rows = conn.execute(f"""
            SELECT c.name, c.color_identity, c.type_line,
                   (col.normalized_name IS NOT NULL) AS in_collection
            FROM cards c
            LEFT JOIN collection col ON col.normalized_name = c.normalized_name
            WHERE {base_where}
              AND lower(c.name) LIKE ?
            ORDER BY c.name
        """, [like]).fetchall()

    return [
        {
            "name": name,
            "colors": _color_symbols(ci),
            "color_names": _color_names(ci),
            "type_line": type_line,
            "in_collection": bool(in_collection),
            "has_deck": (_DECKS_DIR / f"{_deck_filename(name)}.txt").exists(),
        }
        for name, ci, type_line, in_collection in rows
    ]


@app.get("/api/commanders/info")
def get_commander_info(name: str = Query(...)):
    """Return full details for a single commander from the local DB."""
    conn = get_connection()
    row = conn.execute(
        "SELECT name, type_line, oracle_text, mana_cost, cmc, color_identity, edhrec_rank, raw_json "
        "FROM cards WHERE name = ? LIMIT 1",
        [name],
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Commander '{name}' not found")

    c_name, type_line, oracle_text, mana_cost, cmc, color_identity, edhrec_rank, raw_json_str = row
    try:
        data = json.loads(raw_json_str)
        img_uris = data.get("image_uris") or {}
        raw_faces = data.get("card_faces") or []
        if not img_uris and raw_faces:
            img_uris = raw_faces[0].get("image_uris") or {}
        price_usd = data.get("prices", {}).get("usd")
        tcgplayer_url = data.get("purchase_uris", {}).get("tcgplayer", "")
    except Exception:
        img_uris = {}
        raw_faces = []
        price_usd = None
        tcgplayer_url = ""

    # Build per-face data for double-faced cards
    faces = []
    if len(raw_faces) >= 2:
        for face in raw_faces:
            f_img = face.get("image_uris") or {}
            faces.append({
                "name": face.get("name", ""),
                "mana_cost": face.get("mana_cost", ""),
                "type_line": face.get("type_line", type_line or ""),
                "oracle_text": face.get("oracle_text", ""),
                "image": f_img.get("normal", ""),
                "art_crop": f_img.get("art_crop", ""),
            })

    return {
        "name": c_name,
        "type_line": type_line or "",
        "oracle_text": oracle_text or "",
        "mana_cost": mana_cost or "",
        "cmc": int(cmc) if cmc else 0,
        "color_identity": _color_symbols(color_identity),
        "edhrec_rank": edhrec_rank,
        "image": img_uris.get("normal", ""),
        "art_crop": img_uris.get("art_crop", ""),
        "price": float(price_usd) if price_usd else None,
        "tcgplayer_url": tcgplayer_url,
        "has_deck": (_DECKS_DIR / f"{_deck_filename(c_name)}.txt").exists(),
        "faces": faces,
    }


@app.get("/api/commanders/deck")
def get_deck(name: str = Query(...)):
    """Return the pre-built deck for a commander."""
    commander_name = name
    # Try to find the deck file
    safe_name = _deck_filename(commander_name)
    deck_file = _DECKS_DIR / f"{safe_name}.txt"

    if not deck_file.exists():
        # Fuzzy fallback: normalize both sides before comparing
        def _norm(s: str) -> str:
            return re.sub(r"[^a-z0-9 ,]", "_", s.lower())

        target = _norm(safe_name)
        matches = [f for f in _DECKS_DIR.glob("*.txt") if _norm(f.stem) == target]
        if not matches:
            raise HTTPException(status_code=404, detail=f"No deck found for '{commander_name}'")
        deck_file = matches[0]

    raw = deck_file.read_text(encoding="utf-8")
    sections: dict[str, list[str]] = {}
    current_section = "Other"
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^(Commander|Lands|Creatures|Artifacts|Enchantments|Instants|Sorceries|Other)$", line):
            current_section = line
            sections.setdefault(current_section, [])
        elif line.startswith("1 "):
            card_name = line[2:].strip()
            sections.setdefault(current_section, []).append(card_name)

    # Enrich cards with price, image, and oracle data
    conn = get_connection()
    all_cards = [c for cards in sections.values() for c in cards]
    prices: dict[str, float] = {}
    images: dict[str, str] = {}
    card_details: dict[str, dict] = {}

    if all_cards:
        placeholders = ", ".join(["?" for _ in all_cards])
        rows = conn.execute(
            f"SELECT name, oracle_text, type_line, mana_cost, cmc, color_identity, raw_json "
            f"FROM cards WHERE name IN ({placeholders})",
            all_cards,
        ).fetchall()
        for name, oracle_text, type_line, mana_cost, cmc, color_identity, raw_json in rows:
            try:
                data = json.loads(raw_json)
                usd = data.get("prices", {}).get("usd")
                prices[name] = float(usd) if usd else 0.0
                img_uris = data.get("image_uris") or {}
                if not img_uris and data.get("card_faces"):
                    img_uris = data["card_faces"][0].get("image_uris") or {}
                images[name] = img_uris.get("normal", "")
                card_details[name] = {
                    "oracle_text": oracle_text or "",
                    "type_line": type_line or "",
                    "mana_cost": mana_cost or "",
                    "cmc": int(cmc) if cmc is not None else 0,
                    "color_identity": _color_symbols(color_identity),
                    "price": prices[name],
                    "image": images[name],
                    "tcgplayer_url": data.get("purchase_uris", {}).get("tcgplayer", ""),
                }
            except Exception:
                prices[name] = 0.0

    total_price = sum(prices.get(c, 0.0) for c in all_cards)

    return {
        "commander": commander_name,
        "sections": sections,
        "prices": prices,
        "images": images,
        "card_details": card_details,
        "total_price": round(total_price, 2),
        "card_count": sum(len(v) for v in sections.values()),
    }


@app.get("/api/cards/{card_name}/printings")
def get_card_printings(card_name: str):
    """Return image URLs for all printings of a card via Scryfall."""
    q = f'!"{card_name}"'
    url = (
        "https://api.scryfall.com/cards/search?"
        + urllib.parse.urlencode({"q": q, "unique": "prints", "order": "released", "dir": "desc"})
    )
    req = urllib.request.Request(url, headers={"User-Agent": "MTGDeckCreator/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    images = []
    for card in data.get("data", []):
        img_uris = card.get("image_uris") or {}
        if not img_uris and card.get("card_faces"):
            img_uris = card["card_faces"][0].get("image_uris") or {}
        normal = img_uris.get("normal", "")
        if normal:
            images.append({
                "image": normal,
                "set": card.get("set_name", ""),
                "year": (card.get("released_at") or "")[:4],
            })
    return {"images": images}


@app.get("/api/commanders/edhrec")
def get_commander_edhrec(name: str = Query(...)):
    """Fetch commander-specific EDHREC data: rank among commanders, deck count, top themes."""
    slug = _edhrec_slug(name)
    url = f"https://json.edhrec.com/pages/commanders/{slug}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "MTGDeckCreator/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"EDHREC unavailable: {exc}")

    # Navigate to the json_dict — structure: container.json_dict
    json_dict = data.get("container", {}).get("json_dict", {})
    card_info = json_dict.get("card", {})

    num_decks = card_info.get("num_decks") or 0
    commander_rank = card_info.get("rank")  # rank among all commanders on EDHREC

    # Themes are in the top-level panels.taglinks (not inside json_dict)
    # Each taglink: {"count": 6306, "slug": "elves", "value": "Elves"}
    raw_taglinks = data.get("panels", {}).get("taglinks") or []
    themes = [
        {
            "name": t.get("value", ""),
            "num_decks": t.get("count", 0),
            "slug": t.get("slug", ""),
        }
        for t in raw_taglinks
        if t.get("value")
    ][:3]

    return {
        "slug": slug,
        "num_decks": num_decks,
        "commander_rank": commander_rank,
        "themes": themes,
    }


@app.delete("/api/collection")
def delete_collection():
    """Remove all cards from the collection."""
    conn = get_connection()
    conn.execute("DELETE FROM collection")
    return {"deleted": True}


@app.get("/api/collection/status")
def collection_status():
    """Return collection card count and total pre-built decks available on disk."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM collection").fetchone()[0]

    # Count deck files that exist on disk — same check the search endpoint uses
    # for the "deck ready" label, so the number always matches what users see.
    deck_ready = sum(1 for f in _DECKS_DIR.glob("*.txt") if f.is_file())

    return {"count": count, "deck_ready": deck_ready}


_VALID_NAME_COLS = {"name", "card name", "cardname"}


@app.post("/api/collection/upload")
async def upload_collection(
    file: UploadFile = File(...),
    source: str = Query(default="uploaded"),
):
    """Accept a collection CSV upload and ingest it, replacing any previous upload."""
    import csv as _csv
    import io
    from mtgdeck.data.collection_ingest import ingest_collection

    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only .csv files are accepted.",
        )

    content = await file.read()

    # Validate the header before touching the database
    try:
        first_line = content.decode("utf-8-sig").splitlines()[0]
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read the file. Make sure it is a UTF-8 CSV.")

    try:
        header = next(_csv.reader(io.StringIO(first_line)))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse the CSV header row.")

    lower_header = [h.lower().strip() for h in header]
    if not any(col in lower_header for col in _VALID_NAME_COLS):
        raise HTTPException(
            status_code=400,
            detail=(
                f"CSV is missing a card-name column. "
                f"The header must contain one of: {', '.join(sorted(_VALID_NAME_COLS))}. "
                f"Found columns: {', '.join(header) or '(none)'}."
            ),
        )

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb") as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        def _run() -> tuple[int, int]:
            conn = get_connection()
            return ingest_collection(conn, tmp_path, source=source, replace=True)  # type: ignore[arg-type]

        added, skipped = await asyncio.to_thread(_run)
        return {"added": added, "skipped": skipped}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


@app.post("/api/deck/build")
async def build_new_deck(
    commander: str = Query(...),
    owned_only: bool = Query(default=False),
    lands: int = Query(default=36),
):
    """Build a new Commander deck from scratch and return the result."""

    def _run():
        import json as _json
        from mtgdeck.data.duckdb_repo import (
            get_connection, lookup_card_by_name, get_edhrec_recommendations,
            get_collection_names, get_collection_normalized_names,
            collection_count, embedding_count,
        )
        from mtgdeck.data.edhrec_fetch import fetch_edhrec
        from mtgdeck.models import ScryfallCard
        from mtgdeck.rules.commander_rules import is_legal_commander, CommanderProfile
        from mtgdeck.generation.candidate_pool import build_candidate_pool
        from mtgdeck.generation.deck_builder import build_deck, DeckConfig
        from mtgdeck.embeddings.embed_cards import resolve_model_name

        conn = get_connection()

        row = lookup_card_by_name(conn, commander)
        if row is None:
            raise ValueError(f"Commander '{commander}' not found in database.")

        raw = _json.loads(row["raw_json"])
        card = ScryfallCard.model_validate(raw)

        if not is_legal_commander(card):
            raise ValueError(f"'{commander}' is not a legal Commander.")

        profile = CommanderProfile(card=card)

        owned_names: set[str] | None = None
        owned_normalized: set[str] | None = None
        if owned_only:
            if collection_count(conn) == 0:
                raise ValueError("No collection loaded. Upload a collection first.")
            owned_names = get_collection_names(conn)
            owned_normalized = get_collection_normalized_names(conn)

        # Populate EDHREC cache (no-op if already cached)
        try:
            fetch_edhrec(conn, commander)
        except Exception:
            pass
        edhrec_recs = get_edhrec_recommendations(conn, commander)

        # Load embedding index if available.
        # For non-owned builds: use the shared in-memory cache (loaded by startup warmup).
        # If warmup is still in progress, skip vector search (EDHREC-only build, still good quality).
        # For owned-only builds: load a restricted index (not cached — varies per collection).
        embedding_index = None
        model_id = resolve_model_name("local")
        if embedding_count(conn, model_id) > 0:
            from mtgdeck.embeddings.vector_search import load_index
            if owned_normalized is not None:
                embedding_index = load_index(conn, model_id, owned_normalized_names=owned_normalized)
            else:
                with _index_lock:
                    embedding_index = _index_cache.get(model_id)

        candidates = build_candidate_pool(
            conn, profile, edhrec_recs,
            embedding_index=embedding_index,
            model_alias="local",
            owned_names=owned_names,
            owned_only=owned_only,
        )

        config = DeckConfig(
            commander_name=commander,
            num_lands=lands,
            owned_only=owned_only,
            model_alias="local",
        )
        return build_deck(conn, profile, candidates, config)

    try:
        deck = await asyncio.to_thread(_run)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Deck build failed: {exc}")

    # Group cards into display sections
    sections: dict[str, list[str]] = {"Commander": [deck.commander_name]}
    prices: dict[str, float] = {}

    for card in deck.cards:
        name = card.get("name", "")
        if card.get("is_basic_land") or card.get("is_land"):
            section = "Lands"
        elif card.get("is_creature"):
            section = "Creatures"
        elif card.get("is_artifact") and not card.get("is_creature"):
            section = "Artifacts"
        elif card.get("is_enchantment") and not card.get("is_creature") and not card.get("is_artifact"):
            section = "Enchantments"
        elif card.get("is_planeswalker"):
            section = "Planeswalkers"
        elif card.get("is_instant"):
            section = "Instants"
        elif card.get("is_sorcery"):
            section = "Sorceries"
        else:
            section = "Other"

        sections.setdefault(section, []).append(name)

        try:
            raw_data = json.loads(card.get("raw_json", "{}"))
            usd = raw_data.get("prices", {}).get("usd")
            prices[name] = float(usd) if usd else 0.0
        except Exception:
            prices[name] = 0.0

    total_price = sum(prices.get(c, 0.0) for cards_list in sections.values() for c in cards_list)

    # Extract archetypes from warnings for strategy guide
    detected_archetypes: list[str] = []
    for w in (deck.warnings or []):
        import re as _re
        m = _re.search(r"Detected archetypes: (.+)\.", w)
        if m:
            detected_archetypes = [a.strip() for a in m.group(1).split(",")]
            break

    commander_oracle = (deck.commander_row or {}).get("oracle_text", "") or ""
    strategy = _build_strategy_guide(
        commander_name=deck.commander_name,
        commander_oracle=commander_oracle,
        deck_cards=deck.cards,
        archetypes=detected_archetypes,
    )

    return {
        "deck_id": deck.deck_id,
        "commander": deck.commander_name,
        "sections": sections,
        "prices": prices,
        "total_price": round(total_price, 2),
        "card_count": sum(len(v) for v in sections.values()),
        "warnings": deck.warnings,
        "strategy": strategy,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}
