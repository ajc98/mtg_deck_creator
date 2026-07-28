# EDHREC Ingestion and Caching

## Goal

For a given commander, fetch and parse EDHREC recommendation data.

The tool should extract as much useful recommendation data as possible and cache it locally in DuckDB.

## Important Ethics and Practical Rules

Do not overload EDHREC.

Implement:

- local cache,
- polite request delays,
- user-agent header,
- retry logic,
- manual refresh command,
- no repeated fetching during deck generation if cached data exists.

Prefer cache-first behavior.

## Cache Behavior

When the user runs:

```bash
python -m mtgdeck cache-edhrec "K'rrik, Son of Yawgmoth"
```

The tool should:

1. Resolve commander slug.
2. Fetch the EDHREC commander page.
3. Parse recommendation sections.
4. Store raw HTML or JSON snapshot.
5. Store parsed cards and metadata.
6. Store fetch timestamp.
7. Reuse cached data for future deck builds.

## Data to Extract

Try to extract:

- card name,
- category/section,
- synergy score if available,
- percentage of decks if available,
- number of decks if available,
- salt score if available,
- theme/category labels,
- average deck data if available,
- top cards,
- new cards,
- high synergy cards,
- utility lands,
- mana rocks,
- creatures,
- instants,
- sorceries,
- enchantments,
- artifacts,
- planeswalkers.

## Parsing Strategy

EDHREC page structures can change.

Therefore:

1. Store raw page response.
2. Build parser functions with tests.
3. Keep parser resilient.
4. Do not hardcode fragile selectors without fallbacks.
5. If parsing fails, print a helpful message.

## DuckDB Tables

Suggested tables:

```sql
CREATE TABLE IF NOT EXISTS edhrec_pages (
    commander_name TEXT,
    commander_slug TEXT,
    url TEXT,
    fetched_at TIMESTAMP,
    raw_html TEXT,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS edhrec_recommendations (
    commander_name TEXT,
    card_name TEXT,
    section TEXT,
    theme TEXT,
    synergy_score DOUBLE,
    deck_percentage DOUBLE,
    deck_count INTEGER,
    salt_score DOUBLE,
    source_url TEXT,
    fetched_at TIMESTAMP
);
```

## EDHREC Score Normalization

Convert extracted values into normalized features:

- `edhrec_presence_score`: based on percentage of decks.
- `edhrec_synergy_score`: based on synergy number if available.
- `edhrec_section_score`: higher score for cards in key categories.
- `edhrec_confidence_score`: based on data completeness.

## Important

EDHREC data is a recommendation signal, not the only truth.

A card can be strong even if EDHREC score is low, especially if:

- the card is new,
- the card is budget-friendly,
- the card is in the user's collection,
- the card supports a specific subtheme,
- the commander is underrepresented online.
