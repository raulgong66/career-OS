"""Command line interface for CareerOS."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from careeros import (
    CVDocumentRenderer,
    CVOptimizer,
    EntityValidator,
    FileSystemRepository,
    OptimizationStatus,
    OptimizationSummary,
    SchemaLoader,
    generate_artifact as run_artifact_pipeline,
    generate_markdown_cv as run_markdown_cv_pipeline,
    generate_tailored_artifact as run_tailored_artifact_pipeline,
)
from careeros.acquisition import AcquisitionPipeline, DocumentReadError, PipelineError
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
    directory: Optional[Path] = typer.Option(None, "--directory", help="Directory to search. Defaults to the current working directory."),
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


@app.command("generate-markdown-cv")
def generate_markdown_cv(
    profile_file: Path = typer.Argument(..., help="Path to the JSON or YAML profile file."),
    artifact_id: str = typer.Argument(..., help="ID of the CV artifact to generate."),
    output_file: Path = typer.Argument(..., help="Path where the Markdown CV should be written."),
) -> None:
    """Generate a Markdown CV from a canonical profile artifact."""
    schema_loader = SchemaLoader(Path(__file__).resolve().parents[1] / "schemas")
    try:
        markdown = run_markdown_cv_pipeline(profile_file, artifact_id, schema_loader)
        output_path = output_file.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
    except (ValidationError, EntityNotFoundError, OSError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]Generated[/bold green] {output_path}")


@app.command("generate-artifact")
def generate_artifact(
    profile_file: Path = typer.Argument(..., help="Path to the JSON or YAML profile file."),
    artifact_id: str = typer.Argument(..., help="ID of the artifact to generate."),
    output_format: str = typer.Argument(..., help="Output format registered for the artifact type."),
    output_file: Path = typer.Argument(..., help="Path where the generated artifact should be written."),
) -> None:
    """Generate an artifact through the generator registry."""
    schema_loader = SchemaLoader(Path(__file__).resolve().parents[1] / "schemas")
    try:
        output = run_artifact_pipeline(profile_file, artifact_id, output_format, schema_loader)
        output_path = output_file.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(output, bytes):
            output_path.write_bytes(output)
        else:
            output_path.write_text(output, encoding="utf-8")
    except (ValidationError, EntityNotFoundError, OSError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]Generated[/bold green] {output_path}")


@app.command("tailor")
def tailor_artifact(
    profile_file: Path = typer.Argument(..., help="Path to the JSON or YAML profile file."),
    artifact_id: str = typer.Argument(..., help="ID of the CV artifact to tailor."),
    output_format: str = typer.Argument(..., help="Output format for the tailored artifact."),
    output_file: Path = typer.Argument(..., help="Path where the tailored artifact should be written."),
    job_desc: str = typer.Option(None, "--job-desc", help="Job description text or path to a file containing it."),
) -> None:
    """Generate a tailored CV by applying evidence-based ADD recommendations from job description analysis."""
    schema_loader = SchemaLoader(Path(__file__).resolve().parents[1] / "schemas")

    # Resolve job description if it's a file
    job_desc_text = None
    if job_desc:
        desc_path = Path(job_desc).expanduser().resolve()
        if desc_path.exists() and desc_path.is_file():
            try:
                job_desc_text = desc_path.read_text(encoding="utf-8")
            except Exception as exc:
                console.print(f"[bold red]Failed to read job description file: {exc}[/bold red]")
                raise typer.Exit(code=1)
        else:
            job_desc_text = job_desc

    try:
        output = run_tailored_artifact_pipeline(profile_file, artifact_id, output_format, job_desc_text, schema_loader)
        output_path = output_file.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(output, bytes):
            output_path.write_bytes(output)
        else:
            output_path.write_text(output, encoding="utf-8")
    except (ValidationError, EntityNotFoundError, OSError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]Generated tailored artifact[/bold green] {output_path}")


@app.command("optimize-cv")
def optimize_cv(
    profile_file: Path = typer.Argument(..., help="Path to the JSON or YAML profile file."),
    artifact_id: str = typer.Argument(..., help="ID of the CV artifact to optimize."),
    job_desc: str = typer.Option(None, "--job-desc", help="Optional job description text or path to a file containing it."),
    docx: Path = typer.Option(None, "--docx", help="Optional input template DOCX file path."),
    output: Path = typer.Option(None, "--output", help="Optional output DOCX file path."),
) -> None:
    """Optimize a CV artifact by recommending evidence-based additions."""
    try:
        profile_data = _load_payload(profile_file)
    except Exception as exc:
        console.print(f"[bold red]Failed to load profile file: {exc}[/bold red]")
        raise typer.Exit(code=1)

    # Resolve job description if it's a file
    job_desc_text = None
    if job_desc:
        desc_path = Path(job_desc).expanduser().resolve()
        if desc_path.exists() and desc_path.is_file():
            try:
                job_desc_text = desc_path.read_text(encoding="utf-8")
            except Exception as exc:
                console.print(f"[bold red]Failed to read job description file: {exc}[/bold red]")
                raise typer.Exit(code=1)
        else:
            job_desc_text = job_desc

    try:
        optimizer = CVOptimizer(profile_data)
        result = optimizer.optimize_cv(artifact_id, job_desc_text)
    except EntityNotFoundError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[bold red]Optimization error: {exc}[/bold red]")
        raise typer.Exit(code=1)

    if result.status == OptimizationStatus.ALREADY_COMPLETE:
        console.print("[bold green]Your CV is already fully optimized for this opportunity.[/bold green]")
        console.print(f"[dim]{result.message}[/dim]")
        if result.summary:
            _print_summary(result.summary)
        return

    if result.status == OptimizationStatus.NO_MATCHES:
        console.print("[bold yellow]No additions recommended.[/bold yellow]")
        console.print(f"[dim]{result.message}[/dim]")
        if result.summary:
            _print_summary(result.summary)
        return

    recommendations = result.recommendations
    if not recommendations:
        console.print("[bold yellow]Optimization completed with no actionable recommendations.[/bold yellow]")
        return

    table = Table(title=f"Recommended Additions for CV '{artifact_id}'")
    table.add_column("Type", style="cyan")
    table.add_column("Operation", style="green")
    table.add_column("Display Name", style="bold")
    table.add_column("Evidence", style="magenta")
    table.add_column("Total Score", style="yellow", justify="right")
    table.add_column("Scores Breakdown", style="dim")

    for rec in recommendations:
        ev_list = [ev.get("title") or ev.get("id") for ev in rec.evidence]
        ev_str = ", ".join(ev_list) if ev_list else "None"
        
        breakdown = (
            f"JD: {rec.scores.get('job_description_match', 0.0):.1f} | "
            f"Ctx: {rec.scores.get('target_context_match', 0.0):.1f} | "
            f"Ev: {rec.scores.get('evidence_strength', 0.0):.1f}"
        )
        table.add_row(
            rec.type.capitalize(),
            rec.operation,
            rec.display_name,
            ev_str,
            f"{rec.scores.get('weighted_total', 0.0):.2f}",
            breakdown,
        )

    console.print(table)

    if result.summary:
        _print_summary(result.summary)

    if docx or output:
        if not (docx and output):
            console.print("[bold red]Both --docx and --output options must be provided to render updates.[/bold red]")
            raise typer.Exit(code=1)
        
        try:
            renderer = CVDocumentRenderer()
            renderer.apply_recommendations(docx, output, recommendations)
            console.print(f"[bold green]Successfully applied recommendations to {output}[/bold green]")
        except Exception as exc:
            console.print(f"[bold red]Failed to write updated DOCX file: {exc}[/bold red]")
            raise typer.Exit(code=1)


@app.command("acquire-profile")
def acquire_profile(
    source: Path = typer.Argument(..., help="Path to the source document (DOCX)."),
    output: Path = typer.Option(None, "--output", "-o", help="Output path for the generated profile YAML."),
) -> None:
    """Acquire a canonical profile from a source document.

    Parses the document, extracts person information using an LLM,
    builds a canonical profile, validates it against the schema,
    and writes the result to the profiles/ directory.
    """
    pipeline = AcquisitionPipeline()
    try:
        output_path = pipeline.run(source, output)
    except (DocumentReadError, PipelineError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]Profile acquired[/bold green] {output_path}")
    console.print("[green]To validate:[/green] careeros validate profile " + str(output_path))


@app.command("analyze-profile")
def analyze_profile(
    profile_file: Path = typer.Argument(..., help="Path to the JSON or YAML profile file."),
    output: Optional[Path] = typer.Option(None, "--output", help="Write the report as JSON to a file."),
    pretty: bool = typer.Option(False, "--pretty", help="Print a human-readable summary to the console."),
    summary: bool = typer.Option(False, "--summary", help="Print only the summary section."),
) -> None:
    """Run a deterministic analysis of a canonical profile using the Reasoning Engine."""
    try:
        profile_data = _load_payload(profile_file)
    except Exception as exc:
        console.print(f"[bold red]Failed to load profile file: {exc}[/bold red]")
        raise typer.Exit(code=1)

    from careeros.reasoning import ReasoningEngine, create_default_registry

    try:
        registry = create_default_registry()
        engine = ReasoningEngine(registry)
        report = engine.analyze(profile_data)
    except Exception as exc:
        console.print(f"[bold red]Analysis error: {exc}[/bold red]")
        raise typer.Exit(code=1)

    if output:
        output_path = output.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report.to_json(), encoding="utf-8")
        console.print(f"[bold green]Report written[/bold green] {output_path}")
        return

    if pretty:
        s = report.summary
        console.print(f"[bold]Reasoning Report[/bold]")
        console.print(f"  Engine Version: {report.engine_version}")
        console.print(f"  Profile ID:     {report.profile_id}")
        console.print(f"  Generated At:   {report.generated_at.isoformat()}")
        console.print(f"  Total Findings: {s.get('total_findings', 0)}")
        console.print(f"  Rules Executed: {s.get('total_rules_executed', 0)}")
        console.print(f"  Execution Time: {s.get('execution_time_seconds', 0):.2f}s")
        if s.get("findings_by_type_count"):
            console.print(f"  Findings by Type:")
            for ftype, count in s["findings_by_type_count"].items():
                console.print(f"    {ftype}: {count}")
        if s.get("confidence_distribution"):
            console.print(f"  Confidence Distribution:")
            for level, count in sorted(s["confidence_distribution"].items()):
                console.print(f"    {level}: {count}")
        return

    if summary:
        s = report.summary
        console.print(f"Profile ID:     {report.profile_id}")
        console.print(f"Total Findings: {s.get('total_findings', 0)}")
        console.print(f"Rules Executed: {s.get('total_rules_executed', 0)}")
        console.print(f"Execution Time: {s.get('execution_time_seconds', 0):.2f}s")
        return

    console.print_json(report.to_json())


def _print_summary(summary: Any) -> None:
    """Display the optimization summary in the terminal."""
    from careeros import OptimizationSummary

    console.print()
    console.print("[bold]Optimization Summary[/bold]")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Profile Coverage", f"{summary.profile_coverage:.0f}%")
    table.add_row("Profile Elements", f"{summary.included_profile_elements} / {summary.total_profile_elements}")
    table.add_row("Additional Evidence", str(summary.additional_evidence))
    table.add_row("", "")
    table.add_row("Skills Evaluated", str(summary.skills_evaluated))
    table.add_row("Experiences Evaluated", str(summary.experiences_evaluated))
    table.add_row("Projects Evaluated", str(summary.projects_evaluated))
    table.add_row("Achievements Evaluated", str(summary.achievements_evaluated))
    table.add_row("Certifications Evaluated", str(summary.certifications_evaluated))
    table.add_row("Education Evaluated", str(summary.education_evaluated))

    if summary.requirements_detected is not None:
        table.add_row("", "")
        table.add_row("Requirements Detected", str(summary.requirements_detected))
        table.add_row("Requirements Matched", str(summary.requirements_matched))
        table.add_row("Requirement Coverage", f"{summary.requirement_coverage:.0f}%")

    console.print(table)


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
