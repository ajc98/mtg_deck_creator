# MTG Commander Deck Creator — Project Context

Hand this file to Claude at the start of a new session to restore full context.

---

## What This Project Is

A local web app for browsing Magic: The Gathering commanders, viewing pre-built decks, and managing a personal card collection. It is **not** a public service — it runs entirely on localhost.

---

## Architecture

```
mtg_deck_creator/
├── api/                        # FastAPI backend (Python)
│   └── main.py                 # All API endpoints
├── mtgdeck/                    # Core Python package
│   ├── data/
│   │   ├── duckdb_repo.py      # DB connection (DuckDB at ~/.mtgdeck/mtgdeck.duckdb)
│   │   └── collection_ingest.py # CSV upload ingestion (bulk read_csv loader)
│   └── models.py               # normalize_name() and Pydantic models
├── web/                        # Next.js 16 frontend (TypeScript + Tailwind)
│   ├── app/commander/page.tsx  # Main commander browser page (largest file)
│   ├── components/DeckView.tsx # Deck card panel with per-card details
│   └── next.config.ts          # Proxies /api/* → http://localhost:8002/api/*
├── commanders_cleaned/         # Pre-built deck .txt files (one per commander)
└── version_documentation/      # This folder
```

---

## How to Start the App

**API (port 8002):**
```powershell
cd C:\Users\aljic\claude_projects\mtg_deck_creator
uvicorn api.main:app --host 0.0.0.0 --port 8002 --reload
```

**Frontend (port 3000):**
```powershell
cd C:\Users\aljic\claude_projects\mtg_deck_creator\web
npm run dev
```

Then open: `http://localhost:3000/commander`

> Note: `--reload` on uvicorn sometimes does not detect changes on Windows. If changes are not picked up, stop and restart the process manually.

---

## Database

- **Path:** `~/.mtgdeck/mtgdeck.duckdb` (~490 MB)
- **Source:** Scryfall `oracle-cards.json` (one canonical printing per card)
- **Key tables:** `cards`, `collection`
- **Known limitation:** Oracle-cards uses one canonical printing per card. That printing sometimes has `prices.usd = null` even when TCGPlayer has a price (especially Secret Lair / crossover / foil-only cards). The frontend works around this with a live Scryfall fallback.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/commanders/search?q=` | Search legal commanders. Returns `in_collection`, `has_deck`. |
| GET | `/api/commanders/info?name=` | Full commander details: image, price, oracle text, faces, TCGPlayer URL. |
| GET | `/api/commanders/deck?name=` | Pre-built deck sections with enriched card data and total price. |
| GET | `/api/commanders/edhrec?name=` | Live EDHREC data: deck count, rank, top themes. |
| GET | `/api/cards/{card_name}/printings` | All Scryfall printings for a card (images + set). |
| GET | `/api/collection/status` | `{ count, deck_ready }` — collection card count + available deck files. |
| POST | `/api/collection/upload` | Upload a collection CSV. Validates header, replaces existing collection. |
| DELETE | `/api/collection` | Wipe the entire collection. |
| GET | `/api/health` | Health check. |

---

## Frontend Pages & Components

### `web/app/commander/page.tsx`
The entire commander browser lives here. Key sections:

- **`SearchBox`** — Autocomplete dropdown with `ownedOnly` filter toggle. Caches full commander list in `fullListRef`; cache is invalidated via `collectionVersion` counter when collection changes.
- **`CollectionPanel`** — Shows card count + available deck count. Upload CSV button + two-step confirm delete button.
- **`CommanderDetail`** — Full commander info panel: image, oracle text, EDHREC stats, price, TCGPlayer buy link, deck view toggle.
  - Fetches EDHREC data live on commander select.
  - If `info.price` is null/0, does a live Scryfall all-printings search to find the cheapest available price (regular USD preferred, foil USD as fallback for foil-only cards).
- **`DeckView`** (imported component) — Shown when a pre-built deck exists and user clicks "View Deck".

### `web/components/DeckView.tsx`
Deck browser with card detail panel (`CardPanel`).

- Sections: Commander, Lands, Creatures, Artifacts, Enchantments, Instants, Sorceries, Other.
- `CardPanel` fetches live card data from Scryfall (`cards/named?exact=NAME`) for image, oracle text, and price.
- If canonical printing has no price, fetches all printings and picks cheapest (with foil fallback).
- Supports cycling through alternate art printings.
- TCGPlayer buy link shown when available.

---

## Collection CSV Format

The upload endpoint accepts `.csv` files. The file **must** have a column named one of:
- `name`, `card name`, or `cardname` (case-insensitive)

Optional columns (auto-detected): `count`/`quantity`/`qty`, `edition`/`set`, `collector number`, `foil`.

Moxfield exports work out of the box.

---

## Known Issues / In-Progress

### Card Price Not Showing
**Status: being debugged**

Some commanders and deck cards show "Price not in local data" even though TCGPlayer has a price.

**Root cause:** The DB uses Scryfall's oracle-cards canonical printing, which sometimes has `prices.usd = null`. This happens most often for:
- Secret Lair cards (foil-only, `usd` is always null, only `usd_foil` has a value)
- Crossover set cards (LOTR, Avatar: The Last Airbender, Assassin's Creed, TMNT)
- Promo or special-edition cards

**Current fix attempt:** On page load, if `info.price` is null, the frontend queries Scryfall's search API for all printings of the card, filters to those with a USD or USD foil price, and uses the cheapest. Console logging has been added (visible in DevTools → Console, lines prefixed with `[price]`) to diagnose whether the fetch is reaching Scryfall and what it returns.

**Next step:** Check browser DevTools → Console for `[price]` log lines when clicking on a commander with no price. If the fetch reaches Scryfall and returns results, the bug is in the filter/sort. If no log lines appear, the condition `!info.price` is not being triggered (meaning the DB is returning a non-zero price that just isn't being displayed correctly).

**Alternative fix (not yet tried):** Re-ingest the card database from Scryfall's `all-cards.json` instead of `oracle-cards.json`. The all-cards file has one entry per printing (not per card), so prices are much more complete. This is a one-time operation but requires downloading a large file.

---

## Key Technical Decisions Made

| Decision | Reason |
|----------|---------|
| DuckDB bulk insert via `read_csv()` | `executemany` with 3k rows took 53 seconds; `read_csv` bulk loader takes 0.38s |
| `collection_ingest.py` does full DELETE before insert | Simpler than conflict resolution; replace=True always wipes and reloads |
| `collectionVersion` counter pattern | Cache-busts `fullListRef` in SearchBox without re-mounting the component |
| Click-to-toggle tooltip (not hover) | Works on both desktop and mobile |
| `deck_ready` count uses filesystem glob | Using a collection JOIN gave wrong count (0) when collection had unmatched cards |
| Foil price fallback in live fetch | Secret Lair / crossover cards are foil-only — filtering only by `usd` returns empty |

---

## Git History (recent)

```
e813259  Fix archetype expansion to guarantee owned synergy cards enter candidate pool
45b9c86  Add archetype-aware deckbuilding: sacrifice, tokens, graveyard, dragons, voltron, combat, spellslinger
b563289  Rebuild all 321 decks with EDHREC Plan A / Vector Plan B priority
5aeee00  EDHREC = Plan A, Vector = Plan B: two-tier synergy fill + boosted weights
38fb907  Add 321 commander decks built from owned collection
```

Note: All pre-built deck files in `commanders_cleaned/` were deleted by user request (to rebuild them step by step). The folder is currently empty.
