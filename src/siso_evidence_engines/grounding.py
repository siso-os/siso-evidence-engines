"""Dependency-free, ASR-tolerant quote grounding."""

from __future__ import annotations

import difflib
import re
import unicodedata


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text or ""))
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def quote_grounded(quote: str, source_text: str, threshold: float = 0.82) -> tuple[bool, float]:
    """Require every ellipsis-separated quote fragment to occur or fuzzy-match."""
    normalized_source = normalize(source_text)
    source_tokens = normalized_source.split()
    fragments = [fragment for fragment in re.split(r"\.\.\.|…", quote or "") if fragment.strip()]
    if not fragments:
        return False, 0.0
    ratios: list[float] = []
    for fragment in fragments:
        normalized_quote = normalize(fragment)
        if len(normalized_quote) < 4:
            continue
        if normalized_quote in normalized_source:
            ratios.append(1.0)
            continue
        quote_tokens = normalized_quote.split()
        width = len(quote_tokens)
        best = 0.0
        for index in range(0, max(1, len(source_tokens) - width + 1)):
            ratio = difflib.SequenceMatcher(
                None, quote_tokens, source_tokens[index:index + width]
            ).quick_ratio()
            best = max(best, ratio)
            if best >= 0.95:
                break
        ratios.append(best)
    if not ratios:
        return False, 0.0
    weakest = min(ratios)
    return weakest >= threshold, round(weakest, 4)
