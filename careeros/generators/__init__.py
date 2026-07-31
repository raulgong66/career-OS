"""Artifact generators for CareerOS export contracts."""

from .docx_cv import DocxCVGenerator
from .docx_letter import DocxLetterGenerator
from .markdown_cover_letter import MarkdownCoverLetterGenerator
from .markdown_cv import MarkdownCVGenerator
from .registry import ArtifactGenerator, GeneratorRegistry, default_generator_registry

__all__ = [
    "ArtifactGenerator",
    "DocxCVGenerator",
    "DocxLetterGenerator",
    "GeneratorRegistry",
    "MarkdownCoverLetterGenerator",
    "MarkdownCVGenerator",
    "default_generator_registry",
]
