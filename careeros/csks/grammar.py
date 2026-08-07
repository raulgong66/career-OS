"""Deterministic query grammar for the CSKS query engine (M1.23).

The grammar replaces the keyword heuristic that shipped in M1.22 with an
ordered, first-match-wins rule table. Every rule maps a natural-language
question to one of the engine's ``query_type`` values and, where relevant,
extracts the target token (entity name, type noun, milestone number, or
search term) deterministically.

The grammar is pure and standalone: it does not touch the graph, the
index, or any frozen M1.22 component. It only classifies. Graph traversal
and answer assembly remain in ``CSKSQueryEngine``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ClassifiedIntent:
    """Result of classifying a question with the grammar."""

    query_type: str
    target: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    matched_pattern: str | None = None


Extractor = Callable[[str, re.Match], str | None]
Guard = Callable[[str, "ClassifiedIntent"], bool]


@dataclass(frozen=True)
class IntentRule:
    """A single ordered grammar rule."""

    intent: str
    patterns: tuple[str, ...]
    extract_target: Extractor | None = None
    guard: Guard | None = None


def _join(pattern: str, match: re.Match) -> str | None:
    """Return the first non-empty named/grouped capture from a match."""
    for name in ("target", "term", "topic"):
        try:
            value = match.group(name)
        except IndexError:
            continue
        if value:
            return value.strip()
    for group in match.groups():
        if group:
            return group.strip()
    return None


def _extract_after_keyword(pattern: str) -> Extractor:
    """Build an extractor that captures the first regex group."""

    def extract(question: str, match: re.Match) -> str | None:
        return _join(pattern, match)

    return extract


def _flow_topic(question: str, match: re.Match) -> str | None:
    """Extract the data-flow topic, e.g. 'artifact generation' or 'cv'."""
    text = re.sub(
        r"\b(how|does|do|is|are|would|walk|me|through|explain|data|flow|for|"
        r"pipeline|steps|in|sequence|work|works|generated|produced|built|"
        r"created|happen|happens|the|a|an|show|tell)\b",
        " ",
        question,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"[^a-z0-9 ]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text or None


def _target_from_question(question: str, match: re.Match) -> str | None:
    """Fallback target: pull a capitalized token out of the question."""
    hit = re.search(r"\b[A-Z][A-Za-z0-9_.-]+\b", question)
    return hit.group(0) if hit else None


def _capability_guard(question: str, intent: "ClassifiedIntent") -> bool:
    """Capability questions must mention a capability subject."""
    return bool(re.search(
        r"\b(careeros|csks|the system|the platform|it)\b", question, re.IGNORECASE
    ))


def _search_term(question: str, match: re.Match) -> str | None:
    term = _join("term", match)
    if not term:
        return None
    term = re.sub(r"[.?!]+$", "", term).strip()
    if not term or term.lower() in {"the", "for", "a", "an"}:
        return None
    return term


def _milestone_token(question: str, match: re.Match) -> str | None:
    hit = re.search(r"\bm\d+\.\d+\b", question.lower())
    return hit.group(0) if hit else None


def _type_noun(question: str, match: re.Match) -> str | None:
    hit = re.search(r"\b(list(?: all)?|show all|enumerate)\s+(?:the\s+)?(\w+)", question.lower())
    return hit.group(2) if hit else None


def _has_type_noun(question: str) -> bool:
    """True when the question names a CSKS entity type to list."""
    type_keywords = {
        "domain", "domains", "component", "components", "api", "endpoint",
        "endpoints", "cli", "command", "commands", "rule", "rules",
        "generator", "generators", "schema", "schemas", "test", "tests",
        "adr", "adrs", "milestone", "milestones", "config", "configuration",
        "principle", "principles",
    }
    return any(kw in question for kw in type_keywords)


RULES: tuple[IntentRule, ...] = (
    # --- data flow (highest specificity: 'how' collides with other intents) ---
    IntentRule(
        "data_flow_path",
        (
            r"\bhow (does|do|is|are|would) .{0,40}(work|generated|produced|built|created|flow)",
            r"\b(walk me through|explain how|data flow for|flow for|pipeline for|steps in|sequence for)",
        ),
        _flow_topic,
    ),
    # --- reverse dependency ('what does X depend on') ---
    IntentRule(
        "reverse_dependency",
        (
            r"\bwhat (does|do) (?P<target>[\w.]+) depend(?:s)? on\b",
            r"\bwhat are the (?:dependencies|imports) of (?P<target>[\w.]+)\b",
            r"\b(?:dependencies|imports) of (?P<target>[\w.]+)\b",
        ),
        _extract_after_keyword("target"),
    ),
    # --- impact analysis ---
    IntentRule(
        "impact_analysis",
        (
            r"\bwhat breaks if\b",
            r"\bwhat would break if\b",
            r"\bwhat happens if (?:i )?(?:change|modify|remove|refactor)\b",
            r"\bimpact of (?:changing|modifying|removing|changing the)\b",
            r"\bwhat is the impact of\b",
            r"\baffected by\b",
        ),
        _target_from_question,
    ),
    # --- capability check ---
    IntentRule(
        "capability_check",
        (
            r"\bdoes (careeros|csks|the system|the platform) (support|have|include|use)\b",
            r"\bcan (careeros|csks) (support|generate|produce)\b",
            r"\bsupport(?:s)? [a-z0-9 ]{2,40}(generation|export|integration)\b",
            r"\bcapabilit",
        ),
        None,
        _capability_guard,
    ),
    # --- dependency traversal ('what depends on X') ---
    IntentRule(
        "dependency_traversal",
        (
            r"\bwhat depends on\b",
            r"\bdepends upon\b",
            r"\bwhat uses\b",
            r"\bwho uses\b",
            r"\bwhat imports\b",
            r"\bwho consumes\b",
            r"\bconsumers of\b",
            r"\bused by\b",
            r"\bdepends on\b",
        ),
        None,
    ),
    # --- profile quality check (narrative/health questions about a profile) ---
    IntentRule(
        "profile_quality_check",
        (
            r"\bwhy (is|are|isn't|isnt|is not|arent|are not) (the |this |my )?(profile|cv|resume)\b",
            r"\b(why|what makes) (is|are)?(n't| not)? (the |this |my )?(profile|cv|resume) (not |still )?(100%|perfect|healthy|good)\b",
            r"\b(show|list|find|explain|tell me about|what are|what is) (the )?duplicate (narrative|narratives)\b",
            r"\bduplicate (narrative|narratives)\b",
            r"\bnarrative (quality )?(issue|issues)\b",
            r"\bnarrative quality\b",
            r"\b(profile|cv|resume) (health|quality|issues?)\b",
        ),
        None,
        lambda q, i: bool(re.search(
            r"\b(profile|cv|resume|narrative)\b", q, re.IGNORECASE
        )),
    ),
    # --- entity lookup ---
    IntentRule(
        "entity_lookup",
        (
            r"\b(what is|what are|whats|who is|define|describe|tell me about|show me|give me)\b",
            r"\bexplain\b",
        ),
        _target_from_question,
        lambda q, i: bool(re.search(r"\b[A-Z][A-Za-z0-9_.-]+(?:\s+[A-Z][a-z]+)*\b", q))
        or bool(re.search(r"\b[mM]\d+\.\d+\b|\b[A-Z]{2,}[- ]?\d+\b", q)),
    ),
    # --- listing (with an explicit verb) ---
    IntentRule(
        "type_filter",
        (
            r"\b(list|show all|enumerate|list all)\b",
        ),
        _type_noun,
    ),
    # --- status check ---
    IntentRule(
        "status_check",
        (
            r"\b(status|version|tag)\b",
            r"\bm\d+\.\d+\b",
        ),
        _milestone_token,
    ),
    # --- search ---
    IntentRule(
        "search",
        (
            r"\bsearch(?: for)? (?P<term>[\w .-]{2,})\b",
            r"\bfind (?P<term>[\w .-]{2,})\b",
        ),
        _search_term,
    ),
    # --- listing without a verb ('endpoints for profiles', 'cli commands') ---
    IntentRule(
        "type_filter",
        (r"(?i).*",),
        None,
        lambda q, i: _has_type_noun(q),
    ),
)


def classify(question: str) -> "ClassifiedIntent":
    """Classify a question into an intent using first-match-wins rules."""
    cleaned = " ".join(question.split())
    for rule in RULES:
        for pattern in rule.patterns:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if not match:
                continue
            target = None
            if rule.extract_target is not None:
                target = rule.extract_target(cleaned, match)
            intent = ClassifiedIntent(
                query_type=rule.intent,
                target=target,
                params={"matched_pattern": pattern},
            )
            if rule.guard is not None and not rule.guard(cleaned, intent):
                continue
            return intent
    return ClassifiedIntent(query_type="unknown")


def suggest(question: str) -> list[str]:
    """Deterministic suggestions for an unclassifiable question."""
    topic = " ".join(
        t for t in re.findall(r"[A-Za-z][A-Za-z0-9_.-]{2,}", question)
        if t.lower() not in {
            "what", "why", "how", "does", "the", "and", "for", "with", "you",
        }
    )
    if topic:
        topic = topic[:40]
        return [
            f"What is {topic}?",
            f"List {topic}s.",
            f"What depends on {topic}?",
            f"What does {topic} depend on?",
            f"Search {topic}.",
        ]
    return [
        "What is <topic>?",
        "List <type>s.  (e.g. List domains.)",
        "What depends on <entity>?",
        "What does <entity> depend on?",
        "Search <term>.",
    ]
