"""DOCX letter generator (cover letters, interest letters)."""

from __future__ import annotations

from io import BytesIO

from docx import Document

from ..exceptions import ValidationError
from ..export_contract import ExportContract
from .docx_utils import add_inline_text, add_markdown_line
from .markdown_cover_letter import MarkdownCoverLetterGenerator


class DocxLetterGenerator:
    """Generate a minimal DOCX letter from an export contract."""

    supported_artifact_types = {"COVER_LETTER"}

    def __init__(self) -> None:
        """Create a DOCX letter generator backed by the Markdown letter generator."""
        self.markdown_generator = MarkdownCoverLetterGenerator()

    def generate(self, contract: ExportContract) -> bytes:
        """Generate DOCX bytes using only the provided export contract."""
        artifact_type = contract.artifact_type.upper()
        if artifact_type not in self.supported_artifact_types:
            raise ValidationError(f"Unsupported artifact type for DOCX letter: {contract.artifact_type}")

        markdown = self.markdown_generator.generate(contract)
        document = Document()
        for line in markdown.splitlines():
            self._add_markdown_line(document, line)

        buffer = BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def _add_markdown_line(document: Document, line: str) -> None:
        """Thin wrapper that delegates to the shared DOCX markdown helper."""
        add_markdown_line(document, line)

    @staticmethod
    def _add_inline_text(paragraph, text: str) -> None:
        """Thin wrapper that delegates to the shared DOCX inline-text helper."""
        add_inline_text(paragraph, text)
