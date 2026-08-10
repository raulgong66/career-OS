"""CLI sub-application for the Live Repository Checkpoint capability."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .render import render_json, render_markdown
from .service import CheckpointService

CHECKPOINT_APP = typer.Typer(
    name="checkpoint",
    help="Produce a read-only Live Repository Checkpoint.",
    add_completion=False,
    rich_markup_mode="rich",
)
_console = Console()


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@CHECKPOINT_APP.command("live")
def checkpoint_live(
    repo_root: Optional[Path] = typer.Option(
        None,
        "--repo-root",
        "-r",
        help="Repository root (defaults to the CareerOS repository).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit JSON instead of Markdown.",
    ),
) -> None:
    """Collect and render a read-only Live Repository Checkpoint."""
    root = repo_root or _default_repo_root()
    service = CheckpointService(root)
    checkpoint = service.collect()
    if json_output:
        _console.print(render_json(checkpoint), soft_wrap=True)
    else:
        _console.print(render_markdown(checkpoint))