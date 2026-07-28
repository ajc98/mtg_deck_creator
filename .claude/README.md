# MTG Commander Deck Creator — Claude Project Instructions

## Project Goal

Build a Python-first CLI tool that creates legal Magic: The Gathering Commander decks.

The first version must focus on:

1. Commander legality.
2. Color identity legality.
3. 100-card singleton Commander deck construction.
4. Basic land exceptions.
5. Local card database ingestion.
6. Vector search over card text and metadata.
7. EDHREC commander page ingestion/caching.
8. A scoring algorithm that combines:
   - semantic similarity to commander strategy,
   - EDHREC recommendation/frequency signals,
   - card role balance,
   - mana curve,
   - synergy,
   - owned-card availability if collection data is provided.

Do **not** start with Django or React.  
Start with a clean Python CLI and DuckDB-backed local data layer.  
The web UI comes later after the deck-generation engine is reliable.

## Required Tech Stack

Use Python only for the first phase.

Preferred libraries:

- `duckdb` for local analytical database.
- `polars` or `pandas` for data processing.
- `requests` / `httpx` for API and web fetching.
- `beautifulsoup4` or `selectolax` for HTML parsing.
- `pydantic` for schemas and validation.
- `typer` or `click` for CLI.
- `rich` for terminal output.
- `sentence-transformers` or OpenAI embeddings depending on configuration.
- `numpy` / `scikit-learn` for similarity and scoring.

Avoid building the frontend until the CLI has strong results.

## Important Product Principle

This is not just a “find cards with similar text” project.

A good Commander deck often includes cards that do **not** share wording with the commander but are still excellent because they provide:

- ramp,
- mana fixing,
- card draw,
- removal,
- board wipes,
- protection,
- recursion,
- tutors,
- sacrifice outlets,
- token engines,
- combo pieces,
- payoff cards,
- enablers,
- win conditions,
- lands,
- utility lands.

The algorithm must understand deck construction roles, not only card text similarity.

## Expected Output

Given a commander name, the CLI should produce:

- a legal 100-card Commander deck,
- grouped by role,
- with land count,
- mana curve,
- color identity validation,
- explanations for why each card was included,
- scoring breakdown per card,
- warnings if the deck is weak in ramp, draw, removal, lands, curve, or win conditions.

## Suggested CLI Commands

```bash
python -m mtgdeck ingest scryfall --file oracle-cards.json
python -m mtgdeck ingest collection --file moxfield-export.csv
python -m mtgdeck cache-edhrec "K'rrik, Son of Yawgmoth"
python -m mtgdeck build "K'rrik, Son of Yawgmoth" --owned-only
python -m mtgdeck build "Omo, Queen of Vesuva" --allow-unowned --budget 300
python -m mtgdeck explain "K'rrik, Son of Yawgmoth"
python -m mtgdeck validate decklist.txt --commander "K'rrik, Son of Yawgmoth"
```

## Development Order

1. Build card ingestion.
2. Build Commander legality validator.
3. Build DuckDB schema.
4. Build EDHREC cache layer.
5. Build embeddings/vector search.
6. Build scoring engine.
7. Build deck role classifier.
8. Build CLI deck generator.
9. Add deck explanation reports.
10. Only then plan Django + React.
