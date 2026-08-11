"""Deterministic concept retrieval for CSKS (Tier 1).

When the ordered grammar and entity resolver cannot produce a strong answer
(no entity found, an unclassifiable question, an unknown data flow, or a
low-authority entity such as a test), :class:`ConceptRetriever` searches the
source-backed corpus — Markdown document sections, ADRs, domains, components,
and other authoritative entities — for the concepts named by the question.

Everything here is deterministic and offline:

- Tokenization, plural reduction, phrase n-gram extraction, and substring
  matching are rule based; no embeddings, no fuzzy matching, no LLM calls.
- Corpus text comes from repository source files resolved through the same
  provenance used by the rest of CSKS (``source_path`` / ``line_start`` /
  ``line_end``). ADRs match against their full file text because the
  authoritative statement of an ADR spans its sections.
- Ranking is a fixed function: exact phrase match beats token overlap,
  authoritative source types (document > adr > domain > component > ...)
  weigh more than tests/config, and path + line break ties deterministically.
- The result is a bounded :class:`EvidencePack` (1 primary + at most 2
  related), entirely source-backed, suitable for the existing deterministic
  formatter and for a future local-Qwen consumer.

The retriever never invents facts, citations, or answer prose. If no
candidate reaches the minimum threshold, ``retrieve`` returns ``None`` and the
query engine keeps its original (no-evidence) answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import CSKSEvidence, EvidencePack

_MAX_SECTION_CHARS = 800
_MAX_ADR_FILE_CHARS = 6000
_MIN_PRIMARY_SCORE = 2.5
_MAX_RELATED = 2
_MAX_EVIDENCE = 3

_HEADING_RE = re.compile(r"^#{1,6}\s+\S")
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

# Question scaffolding, generic verbs, and filler words that carry no concept
# weight. "system/entity/unknown" are removed so generic questions ("How does
# the system guarantee X?") cannot match on those words alone.
_STOPWORDS = frozenset({
    "what", "whats", "why", "where", "when", "which", "who", "whom", "how",
    "does", "did", "do", "can", "could", "would", "should", "is", "are", "was",
    "were", "be", "been", "the", "and", "or", "of", "in", "on", "at", "for",
    "with", "about", "into", "over", "all", "any", "that", "this", "these",
    "those", "me", "my", "i", "you", "your", "a", "an", "to", "it", "its",
    "as", "from", "by", "give", "tell", "show", "list", "explain", "describe",
    "define", "mean", "means", "called", "known", "system", "systems",
    "entity", "entities", "unknown", "question", "queries", "s", "t", "we",
    "our", "theres", "there",
})

# Authoritative source types, weighted in the task's preferred order.
# Everything outside this set (tests, config, table rows, mermaid edges,
# dependencies, releases, tags) is never a primary concept answer.
_TYPE_WEIGHT = {
    "document": 1.0,
    "adr": 0.95,
    "domain": 0.9,
    "component": 0.85,
    "rule": 0.8,
    "generator": 0.75,
    "milestone": 0.75,
    "api_endpoint": 0.7,
    "cli_command": 0.7,
    "schema": 0.7,
    "principle": 0.65,
}
_AUTHORITATIVE_TYPES = frozenset(_TYPE_WEIGHT)

# Low-authority entity types that should never be a concept answer.
_NOISE_TYPES = frozenset({
    "test", "configuration", "table_row", "mermaid_edge", "dependency",
    "release", "tag",
})

_TYPE_ORDER = {name: index for index, name in enumerate((
    "document", "adr", "domain", "component", "rule", "generator", "milestone",
    "api_endpoint", "cli_command", "schema", "principle",
))}

_TOKEN_SCORE = 1.0
_PHRASE_BONUS = 3.0
_PHRASE_WORD_BONUS = 1.0
_LABEL_PHRASE_BONUS = 1.5
_LABEL_TOKEN_BONUS = 0.75

_RETRIEVAL_LAYER = "deterministic_concept"


@dataclass(frozen=True)
class _Scored:
    score: float
    node: Any
    section: str
    matched_tokens: tuple[str, ...]
    best_phrase: str | None


class ConceptRetriever:
    """Deterministic, source-backed concept retrieval for CSKS questions."""

    def __init__(self, graph, repo_root: "Path | None" = None) -> None:
        from .rich_format import RichFormatter

        self.graph = graph
        self.repo_root = repo_root
        self._formatter = RichFormatter(graph, root=repo_root)
        self._lines_cache: dict[str, list[str] | None] = {}
        self._adr_text_cache: dict[str, str] = {}
        self._corpus: list[tuple[Any, str, str]] | None = None

    # --- corpus -----------------------------------------------------------

    def _read_lines(self, path: str) -> list[str] | None:
        if path not in self._lines_cache:
            try:
                lines = (self.repo_root / path).read_text(encoding="utf-8").splitlines()
            except (OSError, TypeError):
                lines = None
            self._lines_cache[path] = lines
        return self._lines_cache[path]

    def _section_text(self, node) -> str:
        """Source-backed text for the markdown section at ``node.line_start``."""
        path = node.properties.get("source_path", "")
        line = node.properties.get("line_start", 0)
        lines = self._read_lines(path)
        if not lines:
            return ""
        heading_index = None
        for i, ln in enumerate(lines):
            if i + 1 > line:
                break
            if _HEADING_RE.match(ln):
                heading_index = i
        if heading_index is None:
            return ""
        parts: list[str] = []
        for ln in lines[heading_index + 1:]:
            if _HEADING_RE.match(ln):
                break
            parts.append(ln.strip())
        return " ".join(parts)[:_MAX_SECTION_CHARS]

    def _adr_file_text(self, node) -> str:
        """Full normalized text of an ADR file, cached."""
        path = node.properties.get("source_path", "")
        if path not in self._adr_text_cache:
            lines = self._read_lines(path)
            self._adr_text_cache[path] = (
                _NON_ALNUM_RE.sub(" ", " ".join(lines or []).lower())[:_MAX_ADR_FILE_CHARS]
            )
        return self._adr_text_cache[path]

    def _build_corpus(self) -> list[tuple[Any, str, str]]:
        """Return ``(node, section_text, normalized_haystack)`` per authority."""
        entries: list[tuple[Any, str, str]] = []
        for node in self.graph.nodes.values():
            if node.type not in _AUTHORITATIVE_TYPES:
                continue
            section = self._section_text(node)
            if not section:
                section = self._formatter.document_text(node) or ""
            parts = [node.label, node.id, section]
            if node.type == "adr":
                parts.append(self._adr_file_text(node))
            hay = _NON_ALNUM_RE.sub(" ", " ".join(parts).lower())
            entries.append((node, section, hay))
        return entries

    @property
    def corpus(self) -> list[tuple[Any, str, str]]:
        if self._corpus is None:
            self._corpus = self._build_corpus()
        return self._corpus

    # --- query side -------------------------------------------------------

    def retrieve(self, question: str) -> "EvidencePack | None":
        """Return a bounded EvidencePack for a concept question, or None."""
        content = _extract_content(question)
        if not content:
            return None
        phrases = _phrase_variants(content)

        scored: list[_Scored] = []
        for node, section, hay in self.corpus:
            result = _score_candidate(node, section, hay, content, phrases)
            if result is None:
                continue
            scored.append(result)
        if not scored:
            return None

        scored.sort(key=lambda item: (
            -item.score,
            _TYPE_ORDER.get(item.node.type, 99),
            item.node.properties.get("source_path", ""),
            item.node.properties.get("line_start", 0),
        ))

        primary_scored = scored[0]
        if not _passes(primary_scored):
            return None

        primary = self._to_evidence(primary_scored.node, "primary", primary_scored.section)
        related: list[CSKSEvidence] = []
        seen: set[tuple[str, str]] = {(primary.source_path, primary.text)}
        for item in scored[1:]:
            evidence = self._to_evidence(item.node, "related", item.section)
            key = (evidence.source_path, evidence.text)
            if key in seen:
                continue
            seen.add(key)
            related.append(evidence)
            if len(related) >= _MAX_RELATED:
                break

        return EvidencePack(
            query=question,
            primary=primary,
            related=tuple(related),
            retrieval_layer=_RETRIEVAL_LAYER,
            retrieval_score=round(primary_scored.score, 4),
        )

    def _to_evidence(self, node, role: str, section: str) -> "CSKSEvidence":
        text = section or self._formatter.document_text(node) or ""
        return CSKSEvidence(
            entity_id=node.id,
            label=node.label,
            source_path=node.properties.get("source_path", ""),
            line_start=node.properties.get("line_start", 0),
            line_end=node.properties.get("line_end", 0),
            text=text,
            role=role,
        )


def _extract_content(question: str) -> list[str]:
    """Distinct, non-stopword concept tokens from a question, in order."""
    content: list[str] = []
    for token in _TOKEN_RE.findall(question.lower()):
        if len(token) < 2 or token in _STOPWORDS:
            continue
        if token not in content:
            content.append(token)
    return content


def _singular(token: str) -> str:
    """Inflectional plural reduction (safe, rule based)."""
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us")):
        return token[:-1]
    return token


def _variants(token: str) -> list[str]:
    singular = _singular(token)
    return [token, singular] if singular != token else [token]


def _phrase_variants(content: list[str]) -> set[str]:
    """All n-grams (2..5) of the concept tokens plus plural variants."""
    phrases: set[str] = set()
    for i in range(len(content)):
        for j in range(i + 2, min(i + 6, len(content)) + 1):
            base = content[i:j]
            for pi in range(len(base)):
                for variant in _variants(base[pi]):
                    words = base[:pi] + [variant] + base[pi + 1:]
                    phrases.add(" ".join(words))
    return phrases


def _score_candidate(
    node, section: str, hay: str, content: list[str], phrases: set[str]
) -> "_Scored | None":
    matched_tokens = tuple(t for t in content if any(v in hay for v in _variants(t)))
    if not matched_tokens:
        return None
    matched_phrases = sorted(
        (p for p in phrases if p in hay),
        key=lambda p: (len(p.split(" ")), len(p)),
    )
    best_phrase = matched_phrases[-1] if matched_phrases else None

    label_norm = _NON_ALNUM_RE.sub(" ", node.label.lower())
    score = _TOKEN_SCORE * len(matched_tokens)
    if best_phrase is not None:
        score += _PHRASE_BONUS + _PHRASE_WORD_BONUS * len(best_phrase.split(" "))
        if best_phrase in label_norm:
            score += _LABEL_PHRASE_BONUS
    elif any(token in label_norm for token in matched_tokens):
        score += _LABEL_TOKEN_BONUS

    score *= _TYPE_WEIGHT.get(node.type, 0.5)
    return _Scored(score, node, section, matched_tokens, best_phrase)


def _passes(scored: "_Scored") -> bool:
    """A candidate is usable only when it is a strong, authoritative match."""
    if scored.node.type not in _AUTHORITATIVE_TYPES:
        return False
    if scored.score < _MIN_PRIMARY_SCORE:
        return False
    if scored.best_phrase is not None:
        return True
    matched = len(scored.matched_tokens)
    if matched >= 3:
        return True
    if matched >= 2:
        label_norm = _NON_ALNUM_RE.sub(" ", scored.node.label.lower())
        return any(token in label_norm for token in scored.matched_tokens)
    return False
