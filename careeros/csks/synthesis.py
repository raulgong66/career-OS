"""Optional Tier-3 synthesis layer for CSKS (M1.25 boundary).

Consumes an already-validated :class:`EvidencePack` produced by the
deterministic retrieval tiers and synthesizes grounded prose with a local
AIProvider. The provider never retrieves, browses, or searches: it receives
only the question and the bounded evidence, and every claim it makes is
re-grounded against the pack by deterministic post-validation.

This module is the only place that builds the synthesis prompt and parses the
provider's output. It never touches the repository, the knowledge graph, the
index, or the filesystem. After parsing, a deterministic grounding guard
re-checks every concrete number, identifier, and entity token in the answer
against the supplied evidence text, so fabricated facts are refused even when
the JSON shape and evidence ids are valid.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from .models import CSKSEvidence, Citation, EvidencePack

if TYPE_CHECKING:
    from careeros.ai import AIProvider

SYNTHESIS_ENABLED_ENV = "CSKS_SYNTHESIS_ENABLED"
MAX_SYNTHESIS_EVIDENCE = 10
CSKS_SYNTHESIS_TIMEOUT = 30.0

_STATUS_GROUNDED = "grounded"
_STATUS_INSUFFICIENT = "insufficient_evidence"
_STATUS_REFUSAL = "refusal"

_REFUSAL_TEXT = "I could not produce a grounded answer from the supplied evidence."
_INSUFFICIENT_TEXT = "Insufficient evidence to answer the question from the supplied evidence."

SynthesisStatus = Literal["grounded", "insufficient_evidence", "refusal"]

_SYSTEM_INSTRUCTION = (
    "You are a grounded answer synthesizer.\n"
    "\n"
    "Rules:\n"
    "- Answer the user's question using ONLY the evidence supplied in the JSON payload below.\n"
    "- Use no outside knowledge, prior training, or other sources.\n"
    "- Do not invent facts, numbers, entities, or ids.\n"
    "- Every statement must be directly supported by the supplied evidence.\n"
    "- If the evidence is not enough to answer, set status to \"insufficient_evidence\".\n"
    "- If you cannot answer from the evidence alone, set status to \"refusal\".\n"
    "- Return strict JSON only with exactly these fields: "
    "{\"status\": \"grounded\" | \"insufficient_evidence\" | \"refusal\", "
    "\"answer\": string, \"evidence_ids\": [string, ...]}.\n"
    "- When status is \"grounded\", evidence_ids must only contain ids that appear "
    "in the supplied evidence and that support the answer.\n"
    "- Never invent an evidence id that is not present in the supplied evidence."
)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[._,-][A-Za-z0-9]+)*")
_NUMBER_ONLY_RE = re.compile(r"^\d+(?:[.,]\d+)*$")
_CAMELCASE_RE = re.compile(r"[a-z0-9][A-Z]")
_ALL_CAPS_RE = re.compile(r"^[A-Z]{3,}$")
_HYPHEN_TECH_RE = re.compile(r"-[^0-9]*[A-Z0-9]|[A-Z0-9][^0-9]*-")

_CAPITALIZED_STOPWORDS = frozenset(
    {
        "the", "a", "an", "this", "that", "these", "those", "it", "its",
        "in", "on", "at", "for", "with", "by", "from", "to", "of", "and",
        "or", "but", "not", "as", "is", "are", "was", "were", "be", "been",
        "being", "do", "does", "did", "will", "would", "can", "could",
        "should", "may", "might", "must", "there", "their", "they", "we",
        "our", "you", "your", "i", "he", "she", "his", "her", "who", "whom",
        "what", "when", "where", "which", "why", "how", "no", "yes", "than",
        "then", "so", "if", "while", "during", "after", "before", "upon",
        "within", "without", "via", "per", "etc",
    }
)


def _grounding_tokens(answer: str) -> frozenset[str]:
    """Extract the concrete factual tokens a grounded answer must support.

    Categories checked against the evidence: numbers, code-like identifiers
    (dotted/underscored/hyphenated-with-digits), CamelCase or all-caps tokens,
    and capitalized words (excluding sentence-initial words and a small
    English stopword set). Ordinary lowercase prose words are never checked.
    """
    tokens: set[str] = set()
    for sentence in _SENTENCE_BOUNDARY_RE.split(answer.strip()):
        for index, word in enumerate(_WORD_RE.findall(sentence)):
            if _NUMBER_ONLY_RE.match(word):
                tokens.add(word)
                continue
            if "." in word or "_" in word:
                tokens.add(word)
                continue
            if "-" in word and _HYPHEN_TECH_RE.search(word):
                tokens.add(word)
                continue
            if _CAMELCASE_RE.search(word) or _ALL_CAPS_RE.match(word):
                tokens.add(word)
                continue
            if index == 0 or word[0].islower() or word.lower() in _CAPITALIZED_STOPWORDS:
                continue
            tokens.add(word)
    return frozenset(tokens)


def _evidence_text(evidence: list["CSKSEvidence"]) -> str:
    parts: list[str] = []
    for item in evidence:
        parts.append(item.text or "")
        parts.append(item.label or "")
    return "\n".join(parts)


def _grounding_check(answer: str, evidence: list["CSKSEvidence"]) -> bool:
    """Return True only when every concrete token in ``answer`` appears in
    the supplied evidence text (case-insensitive substring match).

    Fail-closed: a clearly unsupported number, identifier, or entity in the
    answer fails the check even when the JSON and evidence ids are valid. A
    pure paraphrase with no concrete tokens passes. False rejection is
    preferred over unsupported factual output.
    """
    tokens = _grounding_tokens(answer)
    if not tokens:
        return True
    haystack = _evidence_text(evidence).lower()
    return all(token.lower() in haystack for token in tokens)


@dataclass(frozen=True)
class SynthesisResult:
    """Validated output of the synthesis layer.

    ``confidence`` is derived deterministically from the EvidencePack, never
    from the provider. ``evidence_ids`` is always a subset of the EvidencePack
    entity ids that survived post-validation.
    """

    status: SynthesisStatus
    answer: str
    evidence_ids: tuple[str, ...]
    confidence: float


def is_synthesis_enabled() -> bool:
    """Return whether the optional synthesis layer is enabled (default off)."""
    return os.environ.get(SYNTHESIS_ENABLED_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def build_prompt(query: str, evidence: list["CSKSEvidence"]) -> str:
    """Build the exact prompt sent to the provider.

    The provider receives only the question and the bounded evidence; nothing
    else from the repository is serialized.
    """
    payload = {
        "query": query,
        "evidence": [
            {
                "entity_id": item.entity_id,
                "label": item.label,
                "source_path": item.source_path,
                "line_start": item.line_start,
                "line_end": item.line_end,
                "text": item.text,
                "role": item.role,
            }
            for item in evidence
        ],
    }
    return _SYSTEM_INSTRUCTION + "\n\n" + json.dumps(payload, ensure_ascii=False, indent=2)


def citations_from_pack(pack: "EvidencePack", evidence_ids: tuple[str, ...]) -> tuple[Citation, ...]:
    """Rebuild citations exclusively from the EvidencePack.

    Provider-supplied citations are never accepted; every citation maps an
    evidence id back to the pack's own source location and text.
    """
    by_id: dict[str, "CSKSEvidence"] = {}
    if pack.primary is not None:
        by_id[pack.primary.entity_id] = pack.primary
    for item in pack.related:
        by_id[item.entity_id] = item

    citations = []
    for entity_id in evidence_ids:
        item = by_id.get(entity_id)
        if item is None:
            continue
        citations.append(
            Citation(
                file=item.source_path,
                line_start=item.line_start,
                line_end=item.line_end,
                text=item.text,
                entity_id=item.entity_id,
            )
        )
    return tuple(citations)


def _confidence_from_pack(pack: "EvidencePack") -> float:
    score = pack.retrieval_score
    if score is not None:
        return min(1.0, score)
    return 1.0 if pack.primary is not None else 0.0


def _parse_json(raw: str):
    text = raw.strip()
    fence = _FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _refusal() -> "SynthesisResult":
    return SynthesisResult(_STATUS_REFUSAL, _REFUSAL_TEXT, (), 0.0)


def _insufficient() -> "SynthesisResult":
    return SynthesisResult(_STATUS_INSUFFICIENT, _INSUFFICIENT_TEXT, (), 0.0)


def _validate_response(raw: str, evidence: list["CSKSEvidence"], pack: "EvidencePack") -> "SynthesisResult":
    """Deterministic post-validation of the provider's structured output."""
    data = _parse_json(raw)
    if data is None or not isinstance(data, dict):
        return _refusal()

    status = data.get("status")
    if not isinstance(status, str):
        return _refusal()
    status = status.strip().lower()

    if status == _STATUS_INSUFFICIENT:
        return _insufficient()
    if status != _STATUS_GROUNDED:
        return _refusal()

    answer = data.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return _refusal()

    raw_ids = data.get("evidence_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        return _refusal()

    pack_ids = {item.entity_id for item in evidence}
    evidence_ids: list[str] = []
    for value in raw_ids:
        if not isinstance(value, str) or not value:
            return _refusal()
        if value not in pack_ids:
            return _refusal()
        if value not in evidence_ids:
            evidence_ids.append(value)
    if not evidence_ids:
        return _refusal()

    answer = answer.strip()
    if not _grounding_check(answer, evidence):
        return _refusal()

    return SynthesisResult(
        status=_STATUS_GROUNDED,
        answer=answer,
        evidence_ids=tuple(evidence_ids),
        confidence=_confidence_from_pack(pack),
    )


class SynthesisEngine:
    """Synthesizes grounded prose from an already-validated EvidencePack.

    The engine holds a provider but never the graph, repository, or index:
    its only input besides the query is the EvidencePack.
    """

    def __init__(self, provider: "AIProvider", max_evidence: int = MAX_SYNTHESIS_EVIDENCE) -> None:
        self.provider = provider
        self.max_evidence = max_evidence

    def synthesize(self, query: str, pack: "EvidencePack") -> "SynthesisResult":
        """Synthesize an answer for ``query`` grounded on ``pack``.

        An empty or invalid pack yields ``insufficient_evidence`` without ever
        invoking the provider.
        """
        evidence = self._bounded_evidence(pack)
        if not evidence:
            return _insufficient()

        prompt = build_prompt(query, evidence)
        try:
            raw = self.provider.generate(prompt, temperature=0.1, timeout=CSKS_SYNTHESIS_TIMEOUT, json_mode=True)
        except Exception:
            return _refusal()

        return _validate_response(raw, evidence, pack)

    def _bounded_evidence(self, pack: "EvidencePack") -> list["CSKSEvidence"]:
        items: list["CSKSEvidence"] = []
        if pack.primary is not None:
            items.append(pack.primary)
        items.extend(pack.related)
        return items[: self.max_evidence]
