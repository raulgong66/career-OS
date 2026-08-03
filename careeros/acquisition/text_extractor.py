from __future__ import annotations

import re


class TextExtractor:
    def extract(self, raw_text: str) -> str:
        text = self._normalize_whitespace(raw_text)
        text = self._remove_excessive_blank_lines(text)
        return text.strip()

    def _normalize_whitespace(self, text: str) -> str:
        lines = text.split("\n")
        normalized = []
        for line in lines:
            line = re.sub(r"[ \t]+", " ", line)
            normalized.append(line)
        return "\n".join(normalized)

    def _remove_excessive_blank_lines(self, text: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", text)
