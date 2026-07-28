# DuckDB Schema

## Purpose

Use DuckDB as the local project database.

DuckDB should store:

- normalized Scryfall cards,
- collection cards,
- EDHREC cached pages,
- EDHREC parsed recommendations,
- embeddings,
- generated decks,
- scoring explanations.

## Tables

```sql
CREATE TABLE IF NOT EXISTS cards (
    oracle_id TEXT,
    scryfall_id TEXT,
    name TEXT,
    normalized_name TEXT,
    type_line TEXT,
    oracle_text TEXT,
    mana_cost TEXT,
    cmc DOUBLE,
    colors TEXT,
    color_identity TEXT,
    keywords TEXT,
    legal_commander BOOLEAN,
    layout TEXT,
    is_basic_land BOOLEAN,
    is_land BOOLEAN,
    is_creature BOOLEAN,
    is_artifact BOOLEAN,
    is_enchantment BOOLEAN,
    is_instant BOOLEAN,
    is_sorcery BOOLEAN,
    is_planeswalker BOOLEAN,
    produced_mana TEXT,
    edhrec_rank INTEGER,
    raw_json TEXT
);
```

```sql
CREATE TABLE IF NOT EXISTS collection (
    normalized_name TEXT,
    name TEXT,
    quantity INTEGER,
    set_code TEXT,
    collector_number TEXT,
    foil BOOLEAN,
    source TEXT
);
```

```sql
CREATE TABLE IF NOT EXISTS card_embeddings (
    normalized_name TEXT,
    embedding_model TEXT,
    embedding DOUBLE[],
    embedded_text TEXT,
    created_at TIMESTAMP
);
```

```sql
CREATE TABLE IF NOT EXISTS edhrec_pages (
    commander_name TEXT,
    commander_slug TEXT,
    url TEXT,
    fetched_at TIMESTAMP,
    raw_html TEXT,
    raw_json TEXT
);
```

```sql
CREATE TABLE IF NOT EXISTS edhrec_recommendations (
    commander_name TEXT,
    card_name TEXT,
    normalized_card_name TEXT,
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

```sql
CREATE TABLE IF NOT EXISTS generated_decks (
    deck_id TEXT,
    commander_name TEXT,
    created_at TIMESTAMP,
    config_json TEXT,
    deck_json TEXT,
    decklist_text TEXT
);
```

```sql
CREATE TABLE IF NOT EXISTS card_scores (
    deck_id TEXT,
    card_name TEXT,
    role TEXT,
    final_score DOUBLE,
    edhrec_score DOUBLE,
    vector_similarity_score DOUBLE,
    role_need_score DOUBLE,
    commander_synergy_score DOUBLE,
    mana_curve_score DOUBLE,
    collection_score DOUBLE,
    budget_score DOUBLE,
    explanation TEXT
);
```

## Name Normalization

Create a deterministic normalization function:

- lowercase,
- remove punctuation where useful,
- normalize apostrophes,
- strip extra whitespace,
- handle split cards carefully.

Do not lose the official card name.
Always preserve original `name`.
