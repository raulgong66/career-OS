"""Artifact generators for CareerOS export contracts."""

from .docx_cv import DocxCVGenerator
from .docx_interest_letter import DocxInterestLetterGenerator
from .docx_letter import DocxLetterGenerator
from .docx_preparation_guide import DocxPreparationGuideGenerator
from .markdown_cover_letter import MarkdownCoverLetterGenerator
from .markdown_cv import MarkdownCVGenerator
from .markdown_interest_letter import MarkdownInterestLetterGenerator
from .markdown_preparation_guide import MarkdownPreparationGuideGenerator
from .registry import ArtifactGenerator, GeneratorRegistry, default_generator_registry

__all__ = [
    "ArtifactGenerator",
    "DocxCVGenerator",
    "DocxInterestLetterGenerator",
    "DocxLetterGenerator",
    "DocxPreparationGuideGenerator",
    "GeneratorRegistry",
    "MarkdownCoverLetterGenerator",
    "MarkdownCVGenerator",
    "MarkdownInterestLetterGenerator",
    "MarkdownPreparationGuideGenerator",
    "default_generator_registry",
]
