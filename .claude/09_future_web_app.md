# Future Web App Plan

## Important

Do not build the web app in phase 1.

Only start this after the CLI can reliably generate and validate decks.

## Future Stack

Backend:

- Django
- Django REST Framework
- DuckDB initially, PostgreSQL later if needed
- Celery/RQ for background deck generation jobs
- Redis for job status if needed

Frontend:

- React
- TypeScript
- Tailwind
- deck visualization components
- filters and scoring explanations

## Future Web Features

- Commander search page.
- Generate deck button.
- Owned collection upload.
- EDHREC cache status.
- Deck role breakdown.
- Mana curve chart.
- Color identity validator.
- Card explanation drawer.
- Score breakdown per card.
- Export to Moxfield/Archidekt text format.
- Compare two generated decks.
- Tune weights with sliders.

## Backend API Ideas

```text
GET /api/commanders/search?q=
POST /api/decks/generate
GET /api/decks/{id}
GET /api/decks/{id}/explanation
POST /api/collections/upload
GET /api/cards/search
```

## Do Not Duplicate Logic

The Django backend should call the same Python engine used by the CLI.

The deck-building logic should live in a reusable Python package, not inside Django views.
