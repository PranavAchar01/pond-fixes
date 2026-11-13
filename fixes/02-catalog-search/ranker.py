"""BM25F-style ranker for PAS catalog items.

Every item is ranked, so a query never returns zero results because one word
is missing. Fields are weighted (name and subtitle count more than the long
description). Tokens get a light suffix stemmer and stopword removal.
An optional synonym table expands query terms; it is off by default so the
plain BM25 result can be reported on its own.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

FIELD_WEIGHTS = {
    "name": 3.0,
    "subtitle": 2.5,
    "useCases": 2.0,
    "categories": 1.5,
    "description": 1.0,
    "summaryClaims": 0.5,
    "requiredConnectorCapabilities": 0.5,
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "do",
    "for",
    "from",
    "get",
    "give",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "please",
    "show",
    "so",
    "that",
    "the",
    "their",
    "them",
    "they",
    "this",
    "to",
    "us",
    "want",
    "we",
    "what",
    "when",
    "which",
    "who",
    "will",
    "with",
    "you",
    "your",
}

# Hand-written, small, and listed in full in the README. Off by default.
SYNONYMS = {
    "fundrais": ["investor", "round", "raise"],
    "pitch": ["investor", "outreach"],
    "complain": ["weak", "complaint", "pain"],
    "conferenc": ["event"],
    "enrich": ["fill", "detail"],
    "monitor": ["watch", "track"],
    "remind": ["reminder", "follow"],
    "shopify": ["storefront", "ecommerc", "platform"],
    "intro": ["introduc"],
    "introduct": ["introduc"],
    "mention": ["listen", "brand"],
}

_TOKEN = re.compile(r"[a-z0-9]+")


def stem(word: str) -> str:
    for suf in (
        "ations",
        "ation",
        "ings",
        "ing",
        "ers",
        "ies",
        "es",
        "ed",
        "er",
        "s",
        "e",
    ):
        if word.endswith(suf) and len(word) - len(suf) >= 4:
            word = word[: -len(suf)] + ("y" if suf == "ies" else "")
            break
    return word


def tokens(text: str) -> list[str]:
    return [
        stem(t)
        for t in _TOKEN.findall(text.lower().replace("_", " "))
        if t not in STOPWORDS
    ]


def _field_text(item: dict, field: str) -> str:
    v = item.get(field) or ""
    return " ".join(v) if isinstance(v, list) else str(v)


@dataclass
class Ranker:
    items: list[dict]
    k1: float = 1.2
    b: float = 0.75
    use_synonyms: bool = False

    def __post_init__(self) -> None:
        self.docs: list[Counter] = []
        lengths = []
        for it in self.items:
            tf: Counter = Counter()
            length = 0.0
            for field, w in FIELD_WEIGHTS.items():
                toks = tokens(_field_text(it, field))
                for t in toks:
                    tf[t] += w
                length += w * len(toks)
            self.docs.append(tf)
            lengths.append(length)
        self.lengths = lengths
        self.avg_len = sum(lengths) / len(lengths) if lengths else 0.0
        df: Counter = Counter()
        for tf in self.docs:
            df.update(tf.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def query_terms(self, query: str) -> list[str]:
        terms = tokens(query)
        if self.use_synonyms:
            extra = [s for t in terms for s in SYNONYMS.get(t, [])]
            terms += extra
        return terms

    def score(self, query: str) -> list[tuple[float, dict]]:
        terms = self.query_terms(query)
        out = []
        for tf, length, it in zip(self.docs, self.lengths, self.items):
            s = 0.0
            for t in terms:
                f = tf.get(t, 0.0)
                if f:
                    norm = self.k1 * (1 - self.b + self.b * length / self.avg_len)
                    s += self.idf[t] * f * (self.k1 + 1) / (f + norm)
            out.append((s, it))
        out.sort(key=lambda p: -p[0])
        return out

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Ranked items with a positive score. Empty only when no query term matches anything."""
        return [it for s, it in self.score(query)[:limit] if s > 0]
