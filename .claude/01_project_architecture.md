# Project Architecture

## Main Modules

```text
mtgdeck/
  __init__.py
  cli.py
  config.py

  data/
    scryfall_ingest.py
    collection_ingest.py
    edhrec_fetch.py
    edhrec_parse.py
    duckdb_repo.py

  rules/
    commander_rules.py
    color_identity.py
    legality.py
    deck_validator.py

  embeddings/
    embed_cards.py
    vector_search.py
    similarity.py

  scoring/
    card_score.py
    deck_score.py
    role_score.py
    mana_curve.py
    land_base.py

  generation/
    commander_profile.py
    candidate_pool.py
    deck_builder.py
    deck_optimizer.py

  output/
    decklist_writer.py
    explanation_report.py
    rich_tables.py

  tests/
    test_color_identity.py
    test_commander_rules.py
    test_deck_validator.py
    test_scoring.py
```

## Data Flow

```text
Scryfall Oracle JSON
        ↓
Normalize card data
        ↓
DuckDB cards table
        ↓
Embeddings table / vector index
        ↓
Commander input
        ↓
Commander profile
        ↓
EDHREC fetch/cache
        ↓
Candidate pool
        ↓
Legality filter
        ↓
Role classification
        ↓
Hybrid scoring
        ↓
Deck construction
        ↓
Deck validation
        ↓
CLI output + explanation report
```

## First Version Constraint

Do not create a web app yet.

The first version should be a CLI because the hard part is not the UI.  
The hard part is building a good deck-selection engine.

## Design Rule

Separate these concerns clearly:

- card data storage,
- Commander rules,
- EDHREC ingestion,
- vector search,
- scoring,
- deck construction,
- output formatting.

Do not mix scraping, scoring, and deck validation in the same function.
