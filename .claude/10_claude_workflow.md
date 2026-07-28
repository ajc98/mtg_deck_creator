# Claude Workflow Instructions

## How Claude Should Work on This Project

Claude should not build everything at once.

Use small implementation steps.

## Preferred Order

1. Create project folder structure.
2. Create config system.
3. Create DuckDB connection/repository.
4. Create Scryfall ingestion.
5. Create Commander legality validator.
6. Create deck validator tests.
7. Create EDHREC cache module.
8. Create parser tests using stored snapshots.
9. Create embeddings module.
10. Create candidate pool generator.
11. Create scoring system.
12. Create deck construction algorithm.
13. Create CLI commands.
14. Create reports/explanations.

## Testing Requirements

Every important MTG rule should have tests.

Tests must include:

- mono-color commander excluding off-color cards,
- colorless cards allowed,
- basic lands allowed multiple times,
- non-basic duplicates rejected,
- Commander-banned cards rejected,
- exactly 100 cards required,
- commander counted as one of the 100,
- owned-only mode excludes unowned cards.

## Claude Should Ask Before

Claude should ask before:

- adding a web framework,
- changing language from Python,
- using a paid API,
- scraping aggressively,
- replacing DuckDB with another database,
- adding manual hardcoded card lists.

## Claude Should Not Ask Before

Claude does not need to ask before:

- creating clean module structure,
- adding tests,
- adding validation,
- improving code organization,
- adding local cache,
- adding docstrings,
- adding CLI help text.

## Quality Bar

The result should feel like a serious data/AI project, not a toy script.

The final engine must be explainable.  
Every included card should have a reason.
