"""Core measurability heuristic — deterministic, module-neutral.

Determines whether a professional statement (typically an achievement
statement) describes a measurable outcome. The heuristic is purely rule-based:
no AI, no LLM, no external services.

This capability was extracted from the private ``_is_measurable`` helper in
``careeros.reasoning.rules.recommendation_rules`` (M1.5) and promoted to a
Core service (M1.17) so that every module — Interview Intelligence, Recruiter
Assistant, Learning Planner, Career Analytics, AI Tailoring — can rely on the
same deterministic signal without importing reasoning internals.
"""

from __future__ import annotations

import re

_BUSINESS_OUTCOME_WORDS: tuple[str, ...] = (
    "reduced",
    "increased",
    "improved",
    "decreased",
    "saved",
    "generated",
    "delivered",
    "achieved",
    "grew",
    "cut",
    "boosted",
    "optimized",
    "automated",
    "accelerated",
    "streamlined",
    "implemented",
    "revenue",
    "cost",
    "costs",
    "sales",
    "profit",
    "margin",
    "roi",
    "efficiency",
    "uptime",
    "availability",
    "performance",
    "latency",
    "turnaround",
    "productivity",
    "growth",
    "conversion",
    "retention",
    "throughput",
    "capacity",
    "scaling",
    "downtime",
    "outage",
    "usd",
    "eur",
    "million",
    "billion",
    "thousand",
)


def _word_boundary_match(word: str, text: str) -> bool:
    """Return ``True`` if ``word`` appears at a word boundary in ``text``.

    Multi-word phrases are matched as substrings; single words use regex
    word-boundary (``\\b``) matching to avoid false positives from partial
    matches (e.g. ``"cost"`` inside ``"costume"``).
    """
    lower_word = word.lower()
    lower_text = text.lower()
    if " " in lower_word:
        return lower_word in lower_text
    return bool(re.search(rf"\b{re.escape(lower_word)}\b", lower_text))


def is_measurable(text: str) -> bool:
    """Return ``True`` if ``text`` describes a measurable outcome.

    The heuristic looks for two signals:

    1. **Digits** — a ``\\d`` character anywhere in the text indicates an
       observable, quantifiable result (percentages, counts, currency, etc.).
    2. **Business-outcome keywords** — verbs and nouns that professional
       recruiters associate with measurable impact (``reduced``, ``increased``,
       ``revenue``, ``uptime``, etc.), matched at word boundaries.

    Returns ``False`` for empty, ``None``-coerced, or purely qualitative text.

    Examples::

        is_measurable("Reduced deployment time by 60%")   → True
        is_measurable("Migrated 240 servers to AWS")       → True
        is_measurable("Responsible for team coordination")  → False
        is_measurable("Worked on various projects")         → False
    """
    if not text:
        return False
    text_stripped = text.strip()
    if not text_stripped:
        return False

    if re.search(r"\d", text_stripped):
        return True

    return any(
        _word_boundary_match(word, text_stripped) for word in _BUSINESS_OUTCOME_WORDS
    )