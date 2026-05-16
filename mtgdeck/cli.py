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
embed_app  = typer.Typer(help="Generate and manage card embeddings.", no_args_is_help=True)
app.add_typer(ingest_app, name="ingest")
app.add_typer(embed_app,  name="embed")

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
# embed cards
# ---------------------------------------------------------------------------


@embed_app.command("cards")
def embed_cards_cmd(
    model: str = typer.Option("local", "--model", "-m", help="Model alias (local, local-large) or HuggingFace ID"),
    batch_size: int = typer.Option(256, "--batch-size", "-b", help="Encoding batch size"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-embed all cards, even if already embedded"),
) -> None:
    """Generate embeddings for all cards in the database."""
    from mtgdeck.data.duckdb_repo import get_connection, embedding_count
    from mtgdeck.embeddings.embed_cards import embed_cards, resolve_model_name

    model_id = resolve_model_name(model)
    conn = get_connection()

    before = embedding_count(conn, model_id)
    console.print(f"[bold]Embedding cards[/bold] with model [cyan]{model_id}[/cyan]")
    if before and not force:
        console.print(f"[dim]{before:,} embeddings already exist. Use --force to re-embed.[/dim]")

    try:
        embedded, skipped = embed_cards(conn, model_alias=model, batch_size=batch_size, force=force)
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    after = embedding_count(conn, model_id)
    console.print(f"\n[green]Done.[/green]  Embedded: {embedded:,}  |  Total in DB: {after:,}")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Free-text semantic search query"),
    commander: str = typer.Option("", "--commander", "-c", help="Restrict to this commander's color identity"),
    model: str = typer.Option("local", "--model", "-m", help="Embedding model alias"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results"),
    min_score: float = typer.Option(0.0, "--min-score", help="Minimum cosine similarity (0–1)"),
    no_lands: bool = typer.Option(False, "--no-lands", help="Exclude land cards"),
) -> None:
    """Semantic vector search over all embedded cards."""
    from mtgdeck.data.duckdb_repo import get_connection, lookup_card_by_name, embedding_count
    from mtgdeck.embeddings.embed_cards import resolve_model_name
    from mtgdeck.embeddings.vector_search import embed_and_search
    from mtgdeck.models import ScryfallCard
    import json

    conn = get_connection()
    model_id = resolve_model_name(model)

    count = embedding_count(conn, model_id)
    if count == 0:
        console.print(
            f"[red]No embeddings found[/red] for model [bold]{model_id}[/bold]. "
            "Run [bold]embed cards[/bold] first."
        )
        raise typer.Exit(1)

    commander_ci: list[str] | None = None
    if commander:
        row = lookup_card_by_name(conn, commander)
        if row is None:
            console.print(f"[red]Commander '{commander}' not found in DB.[/red]")
            raise typer.Exit(1)
        raw = json.loads(row["raw_json"])
        card = ScryfallCard.model_validate(raw)
        commander_ci = card.color_identity

    console.print(
        f"Searching [cyan]{count:,}[/cyan] embedded cards…  "
        f"[dim]query: {query[:60]}{'…' if len(query) > 60 else ''}[/dim]"
    )

    try:
        results = embed_and_search(
            conn,
            query,
            model,
            commander_ci=commander_ci,
            top_k=limit,
            min_score=min_score,
            exclude_lands=no_lands,
        )
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table(title=f"Search results: \"{query[:50]}\"")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Card", style="bold")
    table.add_column("Type")
    table.add_column("CI")
    table.add_column("CMC", justify="right")
    table.add_column("Score", justify="right")

    for i, r in enumerate(results, 1):
        ci_str = "".join(r.color_identity) or "C"
        table.add_row(
            str(i),
            r.name,
            r.type_line[:40],
            ci_str,
            str(int(r.cmc)),
            f"{r.similarity_score:.3f}",
        )

    console.print(table)
    console.print(
        f"[dim]Scores are raw cosine similarity (−1..1). "
        f"Color identity filter: {'/'.join(commander_ci) if commander_ci else 'none'}[/dim]"
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


# ---------------------------------------------------------------------------
# ingest collection
# ---------------------------------------------------------------------------


@ingest_app.command("collection")
def ingest_collection_cmd(
    file: Path = typer.Option(..., "--file", "-f", help="Path to CSV collection file"),
    source: str = typer.Option("manabox", "--source", "-s", help="App that exported the file (manabox, moxfield, archidekt)"),
    replace: bool = typer.Option(False, "--replace", "-r", help="Replace existing collection instead of merging"),
) -> None:
    """Import an owned card collection from a CSV export."""
    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    from mtgdeck.data.duckdb_repo import get_connection
    from mtgdeck.data.collection_ingest import ingest_collection

    conn = get_connection()
    added, skipped = ingest_collection(conn, file, source=source, replace=replace)
    console.print(f"[green]Done.[/green]  Added/updated: {added}  |  Skipped: {skipped}")


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


@app.command("build")
def build_cmd(
    commander: str = typer.Argument(..., help="Commander name"),
    lands: int    = typer.Option(36,    "--lands",   "-l", help="Target land count"),
    model: str    = typer.Option("local","--model",  "-m", help="Embedding model alias"),
    owned_only: bool = typer.Option(False, "--owned-only", help="Only include owned cards"),
    output: Path  = typer.Option(None, "--output", "-o", help="Write decklist text to file"),
    no_explain: bool = typer.Option(False, "--no-explain", help="Skip explanation report"),
) -> None:
    """Build a legal Commander deck for the given commander."""
    import json

    from mtgdeck.data.duckdb_repo import (
        get_connection, lookup_card_by_name, get_edhrec_recommendations,
        get_collection_names, embedding_count,
    )
    from mtgdeck.data.edhrec_fetch import fetch_edhrec
    from mtgdeck.models import ScryfallCard
    from mtgdeck.rules.commander_rules import is_legal_commander, CommanderProfile
    from mtgdeck.rules.deck_validator import validate_deck
    from mtgdeck.generation.candidate_pool import build_candidate_pool
    from mtgdeck.generation.deck_builder import build_deck, DeckConfig
    from mtgdeck.embeddings.embed_cards import resolve_model_name
    from mtgdeck.output.decklist_writer import format_decklist, write_decklist
    from mtgdeck.output.rich_tables import (
        print_deck_summary, print_role_breakdown, print_mana_curve,
        print_validation, print_top_cards,
    )
    from mtgdeck.output.explanation_report import generate_explanation

    conn = get_connection()

    # ── Look up commander ────────────────────────────────────────────────────
    row = lookup_card_by_name(conn, commander)
    if row is None:
        console.print(f"[red]'{commander}'[/red] not found. Run [bold]ingest scryfall[/bold] first.")
        raise typer.Exit(1)

    raw  = json.loads(row["raw_json"])
    card = ScryfallCard.model_validate(raw)

    if not is_legal_commander(card):
        console.print(f"[red]{card.name}[/red] is not a legal Commander.")
        raise typer.Exit(1)

    profile = CommanderProfile(card=card)
    console.print(f"\n[bold]Building deck for:[/bold] [cyan]{card.name}[/cyan]")
    console.print(f"Color identity: {'/'.join(profile.color_identity) or 'Colorless'}")

    # ── Fetch EDHREC data ────────────────────────────────────────────────────
    console.print("\nFetching EDHREC recommendations…")
    try:
        result = fetch_edhrec(conn, commander)
        source = "cache" if result["from_cache"] else "web"
        console.print(f"  {result['card_count']} cards ({source})")
    except (LookupError, RuntimeError) as exc:
        console.print(f"  [yellow]EDHREC unavailable:[/yellow] {exc}  — continuing without it")

    edhrec_recs = get_edhrec_recommendations(conn, commander)

    # ── Load embeddings if available ─────────────────────────────────────────
    embedding_index = None
    model_id = resolve_model_name(model)
    if embedding_count(conn, model_id) > 0:
        from mtgdeck.embeddings.vector_search import load_index
        console.print("Loading embedding index…")
        embedding_index = load_index(conn, model_id)
        console.print(f"  {embedding_index.matrix.shape[0]:,} vectors loaded")
    else:
        console.print("[dim]No embeddings — skipping vector search. Run [bold]embed cards[/bold] to enable it.[/dim]")

    # ── Collection ───────────────────────────────────────────────────────────
    owned_names: set[str] | None = None
    if owned_only:
        owned_names = get_collection_names(conn)
        if not owned_names:
            console.print("[yellow]No collection loaded — ignoring --owned-only.[/yellow]")
            owned_only = False

    # ── Build candidate pool ─────────────────────────────────────────────────
    console.print("\nBuilding candidate pool…")
    candidates = build_candidate_pool(
        conn, profile, edhrec_recs,
        embedding_index=embedding_index,
        model_alias=model,
        owned_names=owned_names,
        owned_only=owned_only,
    )
    console.print(f"  {len(candidates)} candidates")

    if len(candidates) < 30:
        console.print("[yellow]⚠  Fewer than 30 candidates — deck may be weak. Cache EDHREC data and run embed cards.[/yellow]")

    # ── Build deck ───────────────────────────────────────────────────────────
    config = DeckConfig(
        commander_name=commander,
        num_lands=lands,
        owned_only=owned_only,
        model_alias=model,
    )
    console.print("Running deck construction algorithm…")
    deck = build_deck(conn, profile, candidates, config)

    # ── Validate ─────────────────────────────────────────────────────────────
    validation = validate_deck(profile, deck.cards)  # validator adds commander internally

    # ── Output ───────────────────────────────────────────────────────────────
    console.print()
    print_deck_summary(console, deck.commander_name, deck.cards, deck.role_counts, deck.warnings)
    print_role_breakdown(console, deck.role_counts)
    print_mana_curve(console, deck.cards)
    print_validation(console, validation)
    print_top_cards(console, deck.card_scores, limit=15)

    decklist_text = format_decklist(deck.commander_name, deck.cards)
    console.print("\n[bold]Decklist:[/bold]")
    console.print(decklist_text)

    if output:
        write_decklist(output, deck.commander_name, deck.cards)
        console.print(f"[green]Decklist saved to[/green] {output}")

    if not no_explain:
        explanation = generate_explanation(
            deck.commander_name, deck.cards, deck.card_scores,
            deck.role_counts, deck.warnings,
        )
        explain_path = Path(f"{deck.deck_id}_explanation.md")
        explain_path.write_text(explanation, encoding="utf-8")
        console.print(f"[dim]Explanation saved to {explain_path}[/dim]")


# ---------------------------------------------------------------------------
# validate (decklist file)
# ---------------------------------------------------------------------------


@app.command("validate")
def validate_cmd(
    file: Path  = typer.Argument(..., help="Path to a decklist text file"),
    commander: str = typer.Option("", "--commander", "-c", help="Commander name (if not in file)"),
) -> None:
    """Validate a decklist file against Commander rules."""
    import json
    from mtgdeck.data.duckdb_repo import get_connection, lookup_card_by_name
    from mtgdeck.models import ScryfallCard
    from mtgdeck.rules.commander_rules import is_legal_commander, CommanderProfile
    from mtgdeck.rules.deck_validator import validate_deck
    from mtgdeck.output.rich_tables import print_validation

    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    conn = get_connection()
    lines = file.read_text(encoding="utf-8").splitlines()

    card_names: list[str] = []
    commander_name = commander

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Standard format: "1 Card Name" or "Card Name"
        parts = line.split(None, 1)
        if parts[0].isdigit():
            count = int(parts[0])
            name  = parts[1] if len(parts) > 1 else ""
            card_names.extend([name] * count)
        else:
            card_names.append(line)

    if not commander_name and card_names:
        commander_name = card_names[0]

    cmd_row = lookup_card_by_name(conn, commander_name)
    if cmd_row is None:
        console.print(f"[red]Commander '{commander_name}' not found in DB.[/red]")
        raise typer.Exit(1)

    raw  = json.loads(cmd_row["raw_json"])
    card = ScryfallCard.model_validate(raw)

    if not is_legal_commander(card):
        console.print(f"[red]{card.name}[/red] is not a legal Commander.")
        raise typer.Exit(1)

    profile = CommanderProfile(card=card)

    # Look up each card in the deck
    deck_cards: list[dict] = []
    missing: list[str] = []
    for name in card_names:
        row = lookup_card_by_name(conn, name)
        if row is None:
            missing.append(name)
        else:
            deck_cards.append(row)

    if missing:
        console.print(f"[yellow]Cards not in DB ({len(missing)}):[/yellow]")
        for m in missing[:10]:
            console.print(f"  • {m}")
        if len(missing) > 10:
            console.print(f"  … and {len(missing) - 10} more")

    validation = validate_deck(profile, [cmd_row] + deck_cards if cmd_row else deck_cards)
    print_validation(console, validation)


# ---------------------------------------------------------------------------
# explain
# ---------------------------------------------------------------------------


@app.command("explain")
def explain_cmd(
    deck_id: str = typer.Argument(..., help="Deck ID (shown after build)"),
) -> None:
    """Print the explanation report for a previously built deck."""
    from mtgdeck.data.duckdb_repo import get_connection, get_card_scores

    conn = get_connection()
    scores = get_card_scores(conn, deck_id)

    if not scores:
        console.print(f"[red]No scores found for deck ID {deck_id}.[/red]")
        raise typer.Exit(1)

    table = Table(title=f"Card Scores — deck {deck_id[:8]}…")
    table.add_column("Card", style="bold")
    table.add_column("Role")
    table.add_column("Score", justify="right")
    table.add_column("EDHREC", justify="right")
    table.add_column("Vector", justify="right")
    table.add_column("Role Need", justify="right")

    for s in scores:
        table.add_row(
            s["card_name"],
            s["role"] or "—",
            f"{s['final_score']:.3f}",
            f"{s['edhrec_score']:.3f}",
            f"{s['vector_similarity_score']:.3f}",
            f"{s['role_need_score']:.3f}",
        )

    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
