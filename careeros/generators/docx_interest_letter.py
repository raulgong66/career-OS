"""DOCX interest letter generator."""

from __future__ import annotations

from io import BytesIO

from docx import Document

from ..exceptions import ValidationError
from ..export_contract import ExportContract
from .docx_utils import add_markdown_line
from .markdown_interest_letter import MarkdownInterestLetterGenerator


class DocxInterestLetterGenerator:
    """Generate a DOCX interest letter from an export contract."""

    supported_artifact_types = {"INTEREST_LETTER"}

    def __init__(self) -> None:
        self.markdown_generator = MarkdownInterestLetterGenerator()

    def generate(self, contract: ExportContract) -> bytes:
        """Generate DOCX bytes using only the provided export contract."""
        artifact_type = contract.artifact_type.upper()
        if artifact_type not in self.supported_artifact_types:
            raise ValidationError(
                f"Unsupported artifact type for DOCX interest letter: {contract.artifact_type}"
            )

        markdown = self.markdown_generator.generate(contract)
        document = Document()
        for line in markdown.splitlines():
            add_markdown_line(document, line)

        buffer = BytesIO()
        document.save(buffer)
        return buffer.getvalue()
