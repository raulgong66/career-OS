"""DOCX Interview Preparation Guide generator (M1.16)."""

from __future__ import annotations

from io import BytesIO

from docx import Document

from ..exceptions import ValidationError
from ..export_contract import ExportContract
from .docx_utils import add_markdown_line
from .markdown_preparation_guide import MarkdownPreparationGuideGenerator


class DocxPreparationGuideGenerator:
    """Generate a DOCX Interview Preparation Guide from an export contract.

    Reuses the existing DOCX generation architecture: renders Markdown through
    ``MarkdownPreparationGuideGenerator``, then streams every line into a
    ``python-docx`` document via the shared ``docx_utils`` helper.
    """

    supported_artifact_types = {"INTERVIEW_PREPARATION_GUIDE"}

    def __init__(self) -> None:
        self.markdown_generator = MarkdownPreparationGuideGenerator()

    def generate(self, contract: ExportContract) -> bytes:
        artifact_type = contract.artifact_type.upper()
        if artifact_type not in self.supported_artifact_types:
            raise ValidationError(
                f"Unsupported artifact type for DOCX preparation guide:"
                f" {contract.artifact_type}"
            )

        markdown = self.markdown_generator.generate(contract)
        document = Document()
        for line in markdown.splitlines():
            add_markdown_line(document, line)

        buffer = BytesIO()
        document.save(buffer)
        return buffer.getvalue()