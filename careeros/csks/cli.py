"""CSKS CLI commands (M1.22).

Registered into the main ``careeros`` Typer app from ``careeros_cli/main.py``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .indexer import CSKSIndexer
from .query import AnswerFormatter

console = Console()


def _default_repo_root() -> Path:
    """Resolve the repository root relative to this package."""
    return Path(__file__).resolve().parents[2]


def build_csks_app() -> typer.Typer:
    """Return the CSKS sub-application."""
    csks_app = typer.Typer(
        name="csks",
        help="CareerOS Self-Knowledge System: query the repository knowledge graph.",
        add_completion=False,
        rich_markup_mode="rich",
    )

    @csks_app.command("index")
    def index(
        repo_root: Path = typer.Option(None, "--repo-root", help="Repository root. Defaults to the package root."),
    ) -> None:
        """Build the full CSKS index from all sources."""
        root = repo_root or _default_repo_root()
        indexer = CSKSIndexer(root)
        start = time.perf_counter()
        graph = indexer.build_full_index()
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        console.print(f"[bold green]Index built[/bold green] "
                      f"({graph.node_count} nodes, {graph.edge_count} edges, {elapsed_ms}ms)")

    @csks_app.command("query")
    def query(
        question: str = typer.Argument(..., help="Natural-language question to ask the knowledge graph."),
        repo_root: Path = typer.Option(None, "--repo-root", help="Repository root. Defaults to the package root."),
        json_output: bool = typer.Option(False, "--json", help="Emit the result as JSON."),
    ) -> None:
        """Answer a question against the repository knowledge graph."""
        root = repo_root or _default_repo_root()
        indexer = CSKSIndexer(root)
        engine = indexer.get_query_engine()
        result = engine.query(question)
        if json_output:
            console.print_json(json.dumps(AnswerFormatter.format_json(result)))
        else:
            console.print(AnswerFormatter.format_cli(result))

    @csks_app.command("entity")
    def entity(
        entity_id: str = typer.Argument(..., help="Entity ID to inspect."),
        repo_root: Path = typer.Option(None, "--repo-root", help="Repository root. Defaults to the package root."),
    ) -> None:
        """Show a single entity and its relationships."""
        root = repo_root or _default_repo_root()
        indexer = CSKSIndexer(root)
        details = indexer.get_entity(entity_id)
        if details is None:
            console.print(f"[bold red]Entity not found:[/bold red] {entity_id}")
            raise typer.Exit(code=1)

        console.print(f"[bold]{details['id']}[/bold] ({details['type']})")
        console.print(f"Label: {details['label']}")
        table = Table(title="Outgoing Relationships")
        table.add_column("Type")
        table.add_column("Target")
        for rel in details["outgoing_relationships"]:
            table.add_row(rel["type"], rel["target"])
        console.print(table)

        table = Table(title="Incoming Relationships")
        table.add_column("Type")
        table.add_column("Source")
        for rel in details["incoming_relationships"]:
            table.add_row(rel["type"], rel["source"])
        console.print(table)

    @csks_app.command("search")
    def search(
        term: str = typer.Argument(None, help="Search term for grouped results."),
        entity_type: str = typer.Option(None, "--type", help="Filter by entity type."),
        domain: str = typer.Option(None, "--domain", help="Filter by domain property."),
        limit: int = typer.Option(50, "--limit", help="Maximum number of results."),
        repo_root: Path = typer.Option(None, "--repo-root", help="Repository root. Defaults to the package root."),
    ) -> None:
        """Search the knowledge graph. With a <term>, returns grouped results."""
        root = repo_root or _default_repo_root()
        indexer = CSKSIndexer(root)
        if term:
            from .search import grouped_search

            groups = grouped_search(indexer.get_graph(), term, limit=limit)
            if groups["total"] == 0:
                console.print(f"[bold yellow]No entities found matching[/bold yellow] '{term}'.")
                return
            console.print(f'[bold]Search results for "{term}":[/bold]')
            for group_name in (
                "Domains", "Components", "APIs", "Schemas", "Rules",
                "Generators", "Tests", "Milestones", "ADRs",
                "CLI commands", "Configurations", "Documents",
            ):
                items = groups["groups"].get(group_name, [])
                if not items:
                    continue
                console.print(f"[bold]{group_name}:[/bold]")
                for item in items:
                    console.print(f"  - {item['label']} ({item['id']}) — {item['location']}")
            console.print(f"Total matches: {groups['total']}")
            return

        results = indexer.search(entity_type=entity_type, domain=domain, limit=limit)
        table = Table(title="CSKS Entities")
        table.add_column("ID")
        table.add_column("Type")
        table.add_column("Label")
        for item in results:
            table.add_row(item["id"], item["type"], item["label"])
        console.print(table)

    @csks_app.command("status")
    def status(
        repo_root: Path = typer.Option(None, "--repo-root", help="Repository root. Defaults to the package root."),
    ) -> None:
        """Show the current CSKS index status."""
        root = repo_root or _default_repo_root()
        indexer = CSKSIndexer(root)
        info = indexer.get_status()
        table = Table(title="CSKS Index Status")
        table.add_column("Metric")
        table.add_column("Value")
        for key, value in info.items():
            table.add_row(key.replace("_", " ").title(), str(value))
        console.print(table)

    return csks_app


CSKS_APP = build_csks_app()
