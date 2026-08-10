"""Reader for the project-state documentation (``docs/project-state/``).

The checkpoint treats these documents as secondary sources (claims to be
reconciled against live Git/GitHub state), never as authoritative Git state.
Parsing is resilient: a missing or unparseable file yields empty facts plus a
record of what was found, rather than an error.
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import ProjectDocState

_PROJECT_STATE_DIR = "docs/project-state"
_SHA_PATTERN = re.compile(r"\b[0-9a-f]{7,40}\b")


class ProjectStateReader:
    """Parses structured facts out of the project-state Markdown documents."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        self.state_dir = self.repo_root / _PROJECT_STATE_DIR

    @staticmethod
    def _section(text: str, title: str) -> str:
        pattern = rf"^## {re.escape(title)}(?:[ \t].*)?[ \t]*\n(?P<body>(?:.*(?:\n|$))*?)(?=^## |\Z)"
        match = re.search(pattern, text, re.MULTILINE)
        if not match:
            return ""
        return match.group("body").strip()

    @staticmethod
    def _first_bullet(section: str) -> str:
        for line in section.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                return stripped[2:].strip()
        return ""

    @staticmethod
    def _bullets(section: str) -> tuple[str, ...]:
        out = []
        for line in section.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                out.append(stripped[2:].strip())
        return tuple(out)

    @staticmethod
    def _last_bullet(section: str) -> str:
        bullets = ProjectStateReader._bullets(section)
        return bullets[-1] if bullets else ""

    @staticmethod
    def _first_sha(value: str) -> str:
        match = _SHA_PATTERN.search(value or "")
        return match.group() if match else ""

    @staticmethod
    def _first_token(value: str) -> str:
        text = (value or "").strip()
        if not text:
            return ""
        return text.split()[0].strip("`")

    def docs_found(self) -> tuple[str, ...]:
        names: list[str] = []
        current = self.state_dir / "CURRENT_STATE.md"
        if current.exists():
            names.append(current.name)
        names.extend(sorted(p.name for p in self.state_dir.glob("M*-STATE.md")))
        return tuple(names)

    def read_current_state(self) -> ProjectDocState:
        current = self.state_dir / "CURRENT_STATE.md"
        if not current.exists():
            return ProjectDocState(docs_found=self.docs_found())

        try:
            text = current.read_text(encoding="utf-8")
        except OSError:
            return ProjectDocState(docs_found=self.docs_found())

        return ProjectDocState(
            docs_found=self.docs_found(),
            documented_head_sha=self._first_sha(self._first_bullet(self._section(text, "HEAD SHA"))),
            documented_origin_main_sha=self._first_sha(self._first_bullet(self._section(text, "origin/main SHA"))),
            documented_latest_tag=self._first_token(self._first_bullet(self._section(text, "Latest tag"))),
            documented_open_pr_count=self._first_bullet(self._section(text, "Open PRs")),
            documented_test_status=self._first_bullet(self._section(text, "Verified test status")),
            documented_authorized_action=self._first_bullet(self._section(text, "Current authorized action")),
            documented_deferred_items=self._bullets(self._section(text, "Deferred / preservation items")),
            documented_last_checkpoint=self._last_bullet(self._section(text, "Last checkpoint / update")),
        )