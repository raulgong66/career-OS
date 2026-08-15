"""Command line interface for CareerOS."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
import typer
import yaml
from rich.console import Console
from rich.table import Table

load_dotenv()

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
from careeros.checkpoint.cli import CHECKPOINT_APP
from careeros.csks.cli import CSKS_APP
from careeros.exceptions import CareerOSException, DuplicateProfileError, EntityNotFoundError, RepositoryError, SchemaLoadError, ValidationError
from careeros.profile_quality.cli import (
    print_improvement_queue as print_profile_quality_queue,
    print_profile_health,
)
from careeros.profile_repository import ProfileRepository, ProfileState, profile_display_id, profile_display_name
from careeros.reconciliation import (
    load_profiles_for_reconciliation,
    reconcile_profiles,
    write_reconciliation_plan,
)

app = typer.Typer(
    name="careeros",
    help="CareerOS command line interface.",
    add_completion=True,
    rich_markup_mode="rich",
)
app.add_typer(CSKS_APP)
app.add_typer(CHECKPOINT_APP)
console = Console()

PROFILES_APP = typer.Typer(
    name="profiles",
    help="Inspect and manage CareerOS profiles.",
    add_completion=False,
    rich_markup_mode="rich",
)
app.add_typer(PROFILES_APP)


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
            _print_summary(result.summary, optimizer, job_desc_text)
        return

    if result.status == OptimizationStatus.NO_MATCHES:
        console.print("[bold yellow]No additions recommended.[/bold yellow]")
        console.print(f"[dim]{result.message}[/dim]")
        if result.summary:
            _print_summary(result.summary, optimizer, job_desc_text)
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
    table.add_column("Overall match score", style="yellow", justify="right")
    table.add_column("Scores Breakdown", style="dim")

    for rec in recommendations:
        ev_list = [ev.get("title") or ev.get("id") for ev in rec.evidence]
        ev_str = ", ".join(ev_list) if ev_list else "None"
        
        breakdown = (
            f"Requirement match: {rec.scores.get('job_description_match', 0.0):.1f} | "
            f"Context match: {rec.scores.get('target_context_match', 0.0):.1f} | "
            f"Evidence strength: {rec.scores.get('evidence_strength', 0.0):.1f}"
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
        _print_summary(result.summary, optimizer, job_desc_text)

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
    except DuplicateProfileError as exc:
        console.print(f"[bold red]Conflict:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
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


@app.command("profile-health")
def profile_health(
    profile_file: Path = typer.Argument(..., help="Path to canonical profile YAML/JSON"),
    output: str = typer.Option("json", "--output", "-o", help="json|table"),
) -> None:
    """Compute and display profile health score with dimension breakdown."""
    try:
        profile_data = _load_payload(profile_file)
    except Exception as exc:
        console.print(f"[bold red]Failed to load profile file: {exc}[/bold red]")
        raise typer.Exit(code=1)

    try:
        print_profile_health(profile_data, output=output)
    except Exception as exc:
        console.print(f"[bold red]Profile health error: {exc}[/bold red]")
        raise typer.Exit(code=1)


@app.command("improvement-queue")
def improvement_queue(
    profile_file: Path = typer.Argument(..., help="Path to canonical profile YAML/JSON"),
    priority: str = typer.Option(None, "--priority", "-p", help="Filter: high|medium|low"),
    resolution_type: str = typer.Option(None, "--resolution", "-r", help="Filter: auto|guided|none"),
    output: str = typer.Option("json", "--output", "-o", help="json|table"),
) -> None:
    """List prioritized profile-quality findings with resolution actions."""
    try:
        profile_data = _load_payload(profile_file)
    except Exception as exc:
        console.print(f"[bold red]Failed to load profile file: {exc}[/bold red]")
        raise typer.Exit(code=1)

    try:
        print_profile_quality_queue(
            profile_data,
            priority=priority,
            resolution_type=resolution_type,
            output=output,
        )
    except Exception as exc:
        console.print(f"[bold red]Improvement queue error: {exc}[/bold red]")
        raise typer.Exit(code=1)


@PROFILES_APP.command("list")
def profiles_list(
    profiles_root: Path = typer.Option(
        None,
        "--profiles-root",
        help="Profiles directory. Defaults to the repository profiles folder.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the result as JSON.",
    ),
) -> None:
    """List available profiles with their display name and id."""
    root = profiles_root or (Path(__file__).resolve().parents[1] / "profiles")
    records = ProfileRepository(root).list()
    if not records:
        if json_output:
            console.print_json(data=[])
            return
        console.print(f"[bold red]No profiles found in[/bold red] {root}")
        raise typer.Exit(code=1)

    ordered = sorted(records, key=lambda record: profile_display_name(record.data).lower())

    if json_output:
        results = [
            {
                "name": profile_display_name(record.data),
                "id": profile_display_id(record.profile_id),
                "state": record.state.value,
            }
            for record in ordered
        ]
        console.print_json(data=results)
        return

    rows = [
        (profile_display_name(record.data), profile_display_id(record.profile_id))
        for record in ordered
    ]
    name_col = max(len(name) for name, _ in rows) + 2
    id_col = max(len("Profile ID"), *(len(profile_id) for _, profile_id in rows))
    console.print("Available profiles")
    console.print()
    console.print("Name".ljust(name_col) + "Profile ID")
    console.print("-" * (name_col + id_col))
    for name, profile_id in rows:
        console.print(name.ljust(name_col) + profile_id)


@PROFILES_APP.command("show")
def profiles_show(
    profile_id: str = typer.Argument(..., help="Profile ID to inspect."),
    profiles_root: Path = typer.Option(
        None,
        "--profiles-root",
        help="Profiles directory. Defaults to the repository profiles folder.",
    ),
) -> None:
    """Display profile metadata and key metrics."""
    root = profiles_root or (Path(__file__).resolve().parents[1] / "profiles")
    repository = ProfileRepository(root)
    try:
        record = repository.resolve(profile_id)
    except Exception as exc:
        console.print(f"[bold red]Profile not found:[/bold red] {exc}")
        raise typer.Exit(code=1)

    data = record.data
    person = data.get("person", {})
    name = profile_display_name(data)
    display_id = profile_display_id(record.profile_id)
    status = "Archived" if record.state == ProfileState.ARCHIVED else "Active"
    try:
        mtime = datetime.fromtimestamp(record.path.stat().st_mtime, tz=timezone.utc)
        last_modified = mtime.strftime("%Y-%m-%d %H:%M UTC")
    except OSError:
        last_modified = "Unknown"

    experiences = len(data.get("experiences", []))
    skills = len(data.get("skills", []))
    achievements = len(data.get("achievements", []))
    artifacts = len(data.get("artifacts", []))

    health_str = "N/A"
    try:
        from careeros.profile_quality import run_profile_quality
        health_str = f"{run_profile_quality(data).health_score}/100"
    except Exception:
        pass

    summaries = data.get("professionalSummaries", [])
    summary_text = summaries[0].get("text", "") if summaries else ""
    if len(summary_text) > 250:
        summary_text = summary_text[:247] + "..."

    console.print(f"Profile: {name}")
    console.print(f"  Profile ID:   {display_id}")
    console.print(f"  Status:       {status}")
    console.print(f"  Last Modified: {last_modified}")
    console.print(f"  Experiences:  {experiences}")
    console.print(f"  Skills:       {skills}")
    console.print(f"  Achievements: {achievements}")
    console.print(f"  Artifacts:    {artifacts}")
    console.print(f"  Health:       {health_str}")
    if summary_text:
        console.print()
        console.print("  Professional Summary:")
        console.print(f"  {summary_text}")


@PROFILES_APP.command("archive")
def profiles_archive(
    profile_id: str = typer.Argument(..., help="Profile ID to archive."),
    profiles_root: Path = typer.Option(
        None,
        "--profiles-root",
        help="Profiles directory. Defaults to the repository profiles folder.",
    ),
) -> None:
    """Move a profile to the archived state."""
    root = profiles_root or (Path(__file__).resolve().parents[1] / "profiles")
    repository = ProfileRepository(root)
    try:
        resolved = repository.resolve(profile_id)
        record = repository.archive(resolved.profile_id)
    except ValueError as exc:
        console.print(f"[bold red]Archive error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[bold red]Profile not found:[/bold red] {exc}")
        raise typer.Exit(code=1)

    display_id = profile_display_id(record.profile_id)
    console.print(f"[bold green]Archived[/bold green] {display_id}")


@PROFILES_APP.command("restore")
def profiles_restore(
    profile_id: str = typer.Argument(..., help="Profile ID to restore from archive."),
    profiles_root: Path = typer.Option(
        None,
        "--profiles-root",
        help="Profiles directory. Defaults to the repository profiles folder.",
    ),
) -> None:
    """Restore a profile from the archived state back to staging."""
    root = profiles_root or (Path(__file__).resolve().parents[1] / "profiles")
    repository = ProfileRepository(root)
    try:
        resolved = repository.resolve(profile_id)
        if resolved.state != ProfileState.ARCHIVED:
            raise ValueError(
                f"Profile '{profile_display_id(resolved.profile_id)}' is not archived."
            )
        record = repository.restore(resolved.profile_id)
    except Exception as exc:
        console.print(f"[bold red]Restore error:[/bold red] {exc}")
        raise typer.Exit(code=1)

    display_id = profile_display_id(record.profile_id)
    console.print(f"[bold green]Restored[/bold green] {display_id}")


@PROFILES_APP.command("delete")
def profiles_delete(
    profile_id: str = typer.Argument(..., help="Profile ID to permanently delete."),
    force: bool = typer.Option(False, "--force", help="Skip interactive confirmation."),
    profiles_root: Path = typer.Option(
        None,
        "--profiles-root",
        help="Profiles directory. Defaults to the repository profiles folder.",
    ),
) -> None:
    """Permanently delete a profile after interactive confirmation."""
    root = profiles_root or (Path(__file__).resolve().parents[1] / "profiles")
    repository = ProfileRepository(root)
    try:
        record = repository.resolve(profile_id)
    except Exception as exc:
        console.print(f"[bold red]Profile not found:[/bold red] {exc}")
        raise typer.Exit(code=1)

    display_id = profile_display_id(record.profile_id)

    if not force:
        prompt = f"This permanently deletes the profile.\n\nType DELETE to continue: "
        answer = typer.prompt(prompt)
        if answer != "DELETE":
            console.print("[bold red]Aborted.[/bold red]")
            raise typer.Exit(code=1)

    repository.delete(record.profile_id)
    console.print(f"[bold green]Deleted[/bold green] {display_id}")


@PROFILES_APP.command("reconcile")
def profiles_reconcile(
    left_id: str = typer.Argument(..., help="First profile ID to compare."),
    right_id: str = typer.Argument(..., help="Second profile ID to compare."),
    profiles_root: Path = typer.Option(
        None,
        "--profiles-root",
        help="Profiles directory. Defaults to the repository profiles folder.",
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Write reconciliation plan to a YAML file.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the plan as JSON to stdout.",
    ),
) -> None:
    """Compare two profiles and produce a deterministic reconciliation plan.
    
    This command analyzes two profiles and classifies their differences
    without modifying either profile. It compares:
    - Person identity signals (name, email, phone, LinkedIn, GitHub)
    - All profile entities (experiences, organizations, skills, etc.)
    - Provenance metadata (sourceHash, sourceName, importedAt)
    
    The output is a deterministic reconciliation plan suitable for
    human review or programmatic consumption.
    """
    root = profiles_root or (Path(__file__).resolve().parents[1] / "profiles")
    
    left_record, right_record = load_profiles_for_reconciliation(root, left_id, right_id)
    
    if left_record is None:
        console.print(f"[bold red]Profile not found:[/bold red] {left_id}")
        raise typer.Exit(code=1)
    if right_record is None:
        console.print(f"[bold red]Profile not found:[/bold red] {right_id}")
        raise typer.Exit(code=1)
    
    plan = reconcile_profiles(left_record, right_record)
    
    if output:
        out_path = write_reconciliation_plan(plan, output)
        console.print(f"[bold green]Reconciliation plan written[/bold green] {out_path}")
        return
    
    if json_output:
        import json
        console.print_json(data=json.loads(format_reconciliation_plan(plan, output_format="json")))
        return
    
    # Human-readable table output
    from rich.table import Table
    from rich import box
    
    console.print(f"[bold]Reconciliation Plan[/bold]")
    console.print(f"  Left:  {plan.left_profile_id} (person: {plan.left_person_id or 'unknown'})")
    console.print(f"  Right: {plan.right_profile_id} (person: {plan.right_person_id or 'unknown'})")
    console.print()
    
    # Identity comparison
    matched, conflicting = plan.identity_comparison
    console.print("[bold]Identity Comparison[/bold]")
    if matched:
        console.print(f"  Matched: {', '.join(matched)}")
    else:
        console.print("  Matched: (none)")
    if conflicting:
        console.print(f"  Conflicting: {', '.join(conflicting)}")
    else:
        console.print("  Conflicting: (none)")
    console.print()
    
    # Entity diffs summary
    diff_counts = {"SAME": 0, "CONFLICT": 0, "ONLY_IN_LEFT": 0, "ONLY_IN_RIGHT": 0}
    for diff in plan.entity_diffs:
        diff_counts[diff.diff_type.value] += 1
    
    console.print("[bold]Entity Differences[/bold]")
    table = Table(box=box.MINIMAL, padding=(0, 2))
    table.add_column("Type", style="dim")
    table.add_column("Count", justify="right")
    for diff_type, count in diff_counts.items():
        if count > 0:
            table.add_row(diff_type, str(count))
    console.print(table)
    console.print()
    
    # Show conflicts and unique items
    conflicts = [d for d in plan.entity_diffs if d.diff_type == EntityDiffType.CONFLICT]
    if conflicts:
        console.print("[bold]Conflicts[/bold]")
        for diff in conflicts:
            console.print(f"  {diff.entity_type}/{diff.entity_id}: {diff.details}")
        console.print()

    evidence_matches = [d for d in plan.entity_diffs if d.matched_on]
    if evidence_matches:
        console.print("[bold]Evidence Matches[/bold]")
        for diff in evidence_matches:
            matched = f" ({diff.matched_with})" if diff.matched_with else ""
            console.print(f"  {diff.entity_type}/{diff.entity_id}{matched}: on {', '.join(diff.matched_on)}")
        console.print()
    
    left_only = [d for d in plan.entity_diffs if d.diff_type == EntityDiffType.ONLY_IN_LEFT]
    if left_only:
        console.print("[bold]Only in Left[/bold]")
        for diff in left_only:
            console.print(f"  {diff.entity_type}/{diff.entity_id}")
        console.print()
    
    right_only = [d for d in plan.entity_diffs if d.diff_type == EntityDiffType.ONLY_IN_RIGHT]
    if right_only:
        console.print("[bold]Only in Right[/bold]")
        for diff in right_only:
            console.print(f"  {diff.entity_type}/{diff.entity_id}")
        console.print()
    
    # Provenance warnings
    if plan.provenance_warnings:
        console.print("[bold yellow]Provenance Warnings[/bold yellow]")
        for w in plan.provenance_warnings:
            console.print(f"  [{w.warning_type.value}] {w.profile_id}: {w.message}")
        console.print()


# Import needed for the reconcile command
from careeros.reconciliation import EntityDiffType, format_reconciliation_plan


def _print_summary(summary: Any, optimizer: Any = None, job_description: Any = None) -> None:
    """Display the optimization summary in the terminal."""
    from careeros import OptimizationSummary

    console.print()
    console.print("[bold]Optimization Summary[/bold]")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Profile Element Coverage", f"{summary.profile_coverage:.0f}%")
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
        from careeros.reporting import evidence_backed_coverage
        from careeros.reporting.partner_output import jd_concepts_from_text

        table.add_row("", "")
        table.add_row("Requirements Detected", str(summary.requirements_detected))
        table.add_row("Requirements Matched", str(summary.requirements_matched))
        table.add_row("Profile coverage (text match)", f"{summary.requirement_coverage:.0f}%")
        if optimizer is not None and job_description:
            ev_backed = evidence_backed_coverage(
                optimizer, jd_concepts_from_text(job_description)
            )
            table.add_row("Evidence-backed coverage", f"{ev_backed:.0f}%")
            below_text = ev_backed < (summary.requirement_coverage or 0.0)
        else:
            below_text = False

    console.print(table)

    if summary.requirements_detected is not None and optimizer is not None and job_description and below_text:
        console.print(
            "[bold yellow]Note:[/bold yellow] required capabilities are referenced "
            "in this profile but are not all supported by evidence-backed records."
        )


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
