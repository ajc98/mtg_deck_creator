from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="mtgdeck",
    help="MTG Commander Deck Creator",
    no_args_is_help=True,
)
ingest_app = typer.Typer(help="Ingest card data into the local database.", no_args_is_help=True)
app.add_typer(ingest_app, name="ingest")

console = Console()


# ---------------------------------------------------------------------------
# ingest scryfall
# ---------------------------------------------------------------------------


@ingest_app.command("scryfall")
def ingest_scryfall(
    file: Path = typer.Option(..., "--file", "-f", help="Path to Scryfall oracle-cards.json"),
) -> None:
    """Ingest Scryfall Oracle JSON and store cards in DuckDB."""
    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    from mtgdeck.data.duckdb_repo import get_connection, card_count
    from mtgdeck.data.scryfall_ingest import ingest_scryfall as _ingest

    console.print(f"[bold]Loading[/bold] {file} …")
    conn = get_connection()
    before = card_count(conn)

    inserted, skipped, errors = _ingest(conn, file)
    after = card_count(conn)

    console.print()
    table = Table(title="Scryfall Ingest Summary", show_header=False)
    table.add_column("", style="bold")
    table.add_column("")
    table.add_row("Cards in DB before", str(before))
    table.add_row("Cards in DB after", str(after))
    table.add_row("Inserted / updated", str(inserted))
    table.add_row("Skipped (layout/token)", str(skipped))
    table.add_row("Parse errors", str(errors))
    console.print(table)


# ---------------------------------------------------------------------------
# validate-commander
# ---------------------------------------------------------------------------


@app.command("validate-commander")
def validate_commander(
    name: str = typer.Argument(..., help="Commander name to look up and validate"),
) -> None:
    """Look up a card by name and report whether it is a legal Commander."""
    from mtgdeck.data.duckdb_repo import get_connection, lookup_card_by_name
    from mtgdeck.models import ScryfallCard
    from mtgdeck.rules.commander_rules import is_legal_commander
    from mtgdeck.rules.color_identity import format_color_identity, color_identity_name

    conn = get_connection()
    row = lookup_card_by_name(conn, name)

    if row is None:
        console.print(
            f"[red]'{name}'[/red] not found. Run [bold]ingest scryfall[/bold] first."
        )
        raise typer.Exit(1)

    import json
    raw = json.loads(row["raw_json"])
    card = ScryfallCard.model_validate(raw)

    legal = is_legal_commander(card)
    ci = card.color_identity
    ci_str = format_color_identity(ci)
    ci_name = color_identity_name(ci)

    table = Table(title=f"Commander Check: {card.name}", show_header=False)
    table.add_column("", style="bold")
    table.add_column("")
    table.add_row("Name", card.name)
    table.add_row("Type", card.type_line)
    table.add_row("Color Identity", f"{ci_str}  ({ci_name})")
    table.add_row("CMC", str(int(card.cmc)))
    table.add_row("Legal Commander", "[green]YES[/green]" if legal else "[red]NO[/red]")
    table.add_row("Commander legality", card.legalities.get("commander", "unknown"))
    console.print(table)

    if legal:
        console.print(
            f"\n[green]✓[/green] [bold]{card.name}[/bold] can be your Commander."
        )
    else:
        console.print(
            f"\n[red]✗[/red] [bold]{card.name}[/bold] is not a legal Commander."
        )


# ---------------------------------------------------------------------------
# cache-edhrec
# ---------------------------------------------------------------------------


@app.command("cache-edhrec")
def cache_edhrec(
    commander: str = typer.Argument(..., help="Commander name (e.g. \"K'rrik, Son of Yawgmoth\")"),
    force: bool = typer.Option(False, "--force", "-f", help="Bypass cache and fetch fresh data"),
    ttl: int = typer.Option(7, "--ttl", help="Cache TTL in days"),
) -> None:
    """Fetch and cache EDHREC recommendations for a commander."""
    from mtgdeck.data.duckdb_repo import get_connection
    from mtgdeck.data.edhrec_fetch import fetch_edhrec
    from mtgdeck.data.edhrec_parse import slugify

    conn = get_connection()
    slug = slugify(commander)

    console.print(f"[bold]EDHREC cache[/bold] for [cyan]{commander}[/cyan]  (slug: {slug})")

    if not force:
        console.print("Checking local cache…")

    try:
        result = fetch_edhrec(conn, commander, force=force, ttl_days=ttl)
    except LookupError as exc:
        console.print(f"[red]Not found:[/red] {exc}")
        raise typer.Exit(1)
    except RuntimeError as exc:
        console.print(f"[red]Fetch error:[/red] {exc}")
        raise typer.Exit(1)

    source = "[yellow]from cache[/yellow]" if result["from_cache"] else "[green]freshly fetched[/green]"
    console.print(f"Status : {source}")
    console.print(f"URL    : {result['url']}")
    console.print(f"Time   : {result['fetched_at'].strftime('%Y-%m-%d %H:%M UTC')}")
    console.print(f"Cards  : {result['card_count']} recommendation records")


@app.command("edhrec-recs")
def edhrec_recs(
    commander: str = typer.Argument(..., help="Commander name"),
    section: str = typer.Option("", "--section", "-s", help="Filter by section tag (e.g. synergy, top, creatures)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max rows to show"),
) -> None:
    """Show cached EDHREC recommendations for a commander."""
    from mtgdeck.data.duckdb_repo import get_connection, get_edhrec_recommendations, get_edhrec_page

    conn = get_connection()

    page = get_edhrec_page(conn, commander)
    if not page:
        console.print(
            f"[red]No cached data[/red] for '{commander}'. "
            "Run [bold]cache-edhrec[/bold] first."
        )
        raise typer.Exit(1)

    recs = get_edhrec_recommendations(
        conn,
        commander,
        section=section or None,
        limit=limit,
    )

    fetched = page["fetched_at"].strftime("%Y-%m-%d") if page["fetched_at"] else "?"
    title = f"EDHREC: {commander}  (cached {fetched})"
    if section:
        title += f"  [{section}]"

    table = Table(title=title)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Card", style="bold")
    table.add_column("Section")
    table.add_column("Decks %", justify="right")
    table.add_column("Synergy", justify="right")
    table.add_column("Salt", justify="right")

    for i, r in enumerate(recs, 1):
        synergy = f"{r['synergy_score']:.2f}" if r["synergy_score"] is not None else "—"
        salt = f"{r['salt_score']:.2f}" if r["salt_score"] is not None else "—"
        table.add_row(
            str(i),
            r["card_name"],
            r["section"],
            f"{r['deck_percentage']:.1f}%",
            synergy,
            salt,
        )

    console.print(table)
    console.print(f"[dim]Showing {len(recs)} records.[/dim]")


# ---------------------------------------------------------------------------
# db-info
# ---------------------------------------------------------------------------


@app.command("db-info")
def db_info() -> None:
    """Show counts of all tables in the local database."""
    from mtgdeck.data.duckdb_repo import get_connection

    conn = get_connection()
    tables = [
        "cards",
        "collection",
        "card_embeddings",
        "edhrec_pages",
        "edhrec_recommendations",
        "generated_decks",
        "card_scores",
    ]
    table = Table(title="Database Summary")
    table.add_column("Table", style="bold")
    table.add_column("Rows", justify="right")

    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        table.add_row(t, f"{count:,}")

    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
