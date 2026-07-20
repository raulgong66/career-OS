"""Command line interface for CareerOS."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.table import Table

from careeros import EntityValidator, FileSystemRepository, SchemaLoader
from careeros.exceptions import CareerOSException, EntityNotFoundError, RepositoryError, SchemaLoadError, ValidationError

app = typer.Typer(
    name="careeros",
    help="CareerOS command line interface.",
    add_completion=True,
    rich_markup_mode="rich",
)
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Display the CLI help when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command("version")
def version() -> None:
    """Show the installed CareerOS version."""
    console.print("[bold green]CareerOS[/bold green] 1.0.0")


@app.command("doctor")
def doctor() -> None:
    """Check whether the local installation is healthy."""
    repo_root = Path(__file__).resolve().parents[1]
    schema_root = repo_root / "schemas"
    loader = SchemaLoader(schema_root)
    validator = EntityValidator(loader)

    issues: list[str] = []
    if not schema_root.exists():
        issues.append("Schema directory is missing")
    try:
        loader.load_schema("profile")
    except SchemaLoadError as exc:
        issues.append(str(exc))

    valid_profile = {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-1",
            "names": [{"value": "Jane Doe", "usage": "professional"}],
            "contact": {"email": "jane@example.com"},
            "location": {"city": "Stockholm"},
            "positioning": {
                "headline": "Product engineer",
                "valueProposition": "Builds reliable systems",
                "targetDirection": "Growth",
                "themes": ["Engineering"],
            },
        },
    }
    result = validator.validate_entity(valid_profile, "profile")
    if not result.is_valid:
        issues.append("Profile schema validation failed")

    if issues:
        console.print("[bold red]Doctor check failed[/bold red]")
        for issue in issues:
            console.print(f"- {issue}")
        raise typer.Exit(code=1)

    console.print("[bold green]Doctor check passed[/bold green]")


@app.command("schemas")
def schemas() -> None:
    """List available schema entities."""
    loader = SchemaLoader(Path(__file__).resolve().parents[1] / "schemas")
    table = Table(title="Available Schemas")
    table.add_column("Entity")
    for entity in loader.discover_entity_names():
        table.add_row(entity)
    console.print(table)


@app.command("schemas-info")
def schemas_info(entity: str = typer.Argument(..., help="Entity name to inspect.")) -> None:
    """Show schema metadata for a specific entity."""
    loader = SchemaLoader(Path(__file__).resolve().parents[1] / "schemas")
    try:
        schema = loader.load_schema(entity)
    except SchemaLoadError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold]{schema.get('title', entity)}[/bold]")
    console.print(schema.get("description", "No description available."))
    console.print(f"Version: {schema.get('version', 'unknown')}")


@app.command("validate")
def validate_entity(
    entity: str = typer.Argument(..., help="Entity schema name to validate against."),
    file_path: Path = typer.Argument(..., help="Path to the JSON or YAML file to validate."),
) -> None:
    """Validate an entity file against the matching schema."""
    loader = SchemaLoader(Path(__file__).resolve().parents[1] / "schemas")
    validator = EntityValidator(loader)
    try:
        result = EntityValidator.validate_file(file_path, entity, loader)
    except (ValidationError, FileNotFoundError, OSError, yaml.YAMLError, json.JSONDecodeError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    if result.is_valid:
        console.print("[bold green]Validation passed[/bold green]")
    else:
        console.print("[bold red]Validation failed[/bold red]")
        for error in result.errors:
            console.print(f"- {error['path']}: {error['message']}")
        raise typer.Exit(code=1)


@app.command("create")
def create_entity(
    entity: str = typer.Argument(..., help="Entity schema name to create."),
    output_file: Path = typer.Argument(..., help="Path where the new entity should be written."),
) -> None:
    """Create a starter entity file from the selected schema."""
    loader = SchemaLoader(Path(__file__).resolve().parents[1] / "schemas")
    schema = loader.load_schema(entity)
    starter = _starter_payload(schema)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(starter, indent=2), encoding="utf-8")
    console.print(f"[bold green]Created[/bold green] {output_file}")


@app.command("show")
def show_entity(
    entity: str = typer.Argument(..., help="Entity type name."),
    file_path: Path = typer.Argument(..., help="Path to the entity file."),
) -> None:
    """Display the contents of an entity file."""
    payload = _load_payload(file_path)
    console.print_json(json.dumps(payload))


@app.command("list")
def list_entities(
    entity: str = typer.Argument(..., help="Entity type name."),
    directory: Path = typer.Argument(..., help="Directory containing entity files."),
) -> None:
    """List entity files from a directory."""
    directory = directory.expanduser().resolve()
    items = sorted(path for path in directory.glob("*.json") if path.is_file())
    for item in items:
        console.print(item.stem)


@app.command("search")
def search_entities(
    entity: str = typer.Argument(..., help="Entity type name."),
    field: str = typer.Argument(..., help="Field to match."),
    value: str = typer.Argument(..., help="Value to search for."),
    directory: Path | None = typer.Option(None, "--directory", help="Directory to search. Defaults to the current working directory."),
) -> None:
    """Search entity files for a matching field value."""
    search_directory = (directory or Path.cwd()).expanduser().resolve()
    matches: list[str] = []
    for item in sorted(search_directory.glob("*.json")):
        payload = _load_payload(item)
        if payload.get(field) == value:
            matches.append(item.name)
    if matches:
        for match in matches:
            console.print(match)
    else:
        console.print("No matches found")


def _load_payload(file_path: Path) -> dict[str, Any]:
    """Load a JSON or YAML payload from disk."""
    path = file_path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def _starter_payload(schema: dict[str, Any]) -> dict[str, Any]:
    """Create a minimal starter payload for an entity schema."""
    payload: dict[str, Any] = {}
    for name, value in schema.get("properties", {}).items():
        if name in {"id", "metadata"}:
            continue
        if value.get("type") == "object":
            payload[name] = {}
        elif value.get("type") == "array":
            payload[name] = []
        elif value.get("type") == "string":
            payload[name] = ""
        elif value.get("type") == "number":
            payload[name] = 0
        elif value.get("type") == "boolean":
            payload[name] = False
        else:
            payload[name] = None
    return payload


if __name__ == "__main__":
    app()
