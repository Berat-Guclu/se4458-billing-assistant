from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TOKEN = re.compile(r"[a-z0-9]+")
HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
SECTION_NUMBER = re.compile(r"^(\d+(?:\.\d+)*)")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "can",
    "do",
    "does",
    "for",
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
    "per",
    "the",
    "this",
    "that",
    "to",
    "what",
    "when",
    "why",
    "with",
    "you",
    "your",
    "much",
}


@dataclass(frozen=True)
class Chunk:
    section: str
    title: str
    body: str

    @property
    def excerpt(self) -> str:
        text = self.body.strip()
        if len(text) <= 700:
            return text
        return text[:700].rstrip() + "..."


class BillingIndex:
    """Section index built once from the billing guide. Search does not rebuild it."""

    def __init__(self, markdown: str):
        self.chunks = split_markdown(markdown)

    @classmethod
    def from_file(cls, path: Path) -> "BillingIndex":
        return cls(path.read_text(encoding="utf-8"))

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    def search(self, query: str, limit: int = 3) -> list[dict]:
        terms = tokenize(query)
        if not terms:
            return []
        phrase = " ".join(terms)
        scored: list[tuple[int, Chunk]] = []
        for chunk in self.chunks:
            weight = score_chunk(chunk, terms, phrase)
            if weight > 0:
                scored.append((weight, chunk))
        scored.sort(key=lambda item: (-item[0], item[1].section))
        return [
            {
                "section": chunk.section,
                "title": chunk.title,
                "excerpt": chunk.excerpt,
                "score": weight,
            }
            for weight, chunk in scored[:limit]
        ]

    def search_text(self, query: str, limit: int = 3) -> str:
        if not query or not query.strip():
            return "No query was provided."
        hits = self.search(query, limit=limit)
        if not hits:
            return "No matching billing policy section was found."
        blocks = [
            f"Section {hit['section']}: {hit['title']}\n{hit['excerpt']}"
            for hit in hits
        ]
        return "\n\n".join(blocks)


def split_markdown(markdown: str) -> list[Chunk]:
    matches = list(HEADING.finditer(markdown))
    chunks: list[Chunk] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        title = match.group(2).strip()
        body = markdown[start:end].strip()
        if not body:
            continue
        number = SECTION_NUMBER.match(title)
        section = number.group(1) if number else title
        chunks.append(Chunk(section=section, title=title, body=body))
    return chunks


def tokenize(query: str) -> list[str]:
    terms = []
    for token in TOKEN.findall(query.lower()):
        if token not in STOPWORDS and token not in terms:
            terms.append(token)
    return terms


def score_chunk(chunk: Chunk, terms: list[str], phrase: str) -> int:
    title = chunk.title.lower()
    body = chunk.body.lower()
    weight = 0
    for term in terms:
        weight += min(_count_term(body, term), 4) * 2
        weight += _count_term(title, term) * 6
    if phrase and phrase in f"{title}\n{body}":
        weight += 8
    return weight


def _count_term(text: str, term: str) -> int:
    return len(re.findall(rf"\b{re.escape(term)}\b", text))
