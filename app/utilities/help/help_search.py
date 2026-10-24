"""
Searching the help articles of one language: every word of the query is
looked for in the title, the keywords, the summary and the body (also
without its last letters, so "переадресацию" finds "переадресация"); the
articles that match the most words, in the most telling places, come
first, each with the passage of its body that matched.
"""

import re
from dataclasses import dataclass

from app.schemas.dto.help import HelpArticleRecord

TITLE_WEIGHT: int = 8
KEYWORD_WEIGHT: int = 5
SUMMARY_WEIGHT: int = 3
BODY_WEIGHT: int = 1
BODY_MATCH_CAP: int = 3
STEM_WEIGHT_DIVISOR: int = 2
MIN_TERM_LENGTH: int = 2
STEM_FROM_LENGTH: int = 6
STEM_TRIM: int = 2
SNIPPET_RADIUS: int = 90
MAX_TERMS: int = 8

WORD_PATTERN: re.Pattern[str] = re.compile(r"[\w'’]+", re.UNICODE)
LINK_PATTERN: re.Pattern[str] = re.compile(r"\[([^\]]*)\]\([^)]*\)")
MARKUP_PATTERN: re.Pattern[str] = re.compile(r"[*_`>#|]+")
SPACE_PATTERN: re.Pattern[str] = re.compile(r"\s+")
LIST_MARKER_PATTERN: re.Pattern[str] = re.compile(r"(^|\n)\s*(?:[-+]|\d+\.)\s+")


@dataclass(frozen=True)
class SearchMatch:
    article: HelpArticleRecord
    matched_terms: int
    score: int
    snippet: str | None


def search_terms(text: str) -> list[str]:
    """The distinct words of a query, in order, case-folded."""

    terms: list[str] = []
    for word in WORD_PATTERN.findall(text.casefold()):
        if len(word) >= MIN_TERM_LENGTH and word not in terms:
            terms.append(word)
    return terms[:MAX_TERMS]


def plain_text(markdown: str) -> str:
    """Markdown as one line of readable text (links keep their words)."""

    text: str = LINK_PATTERN.sub(r"\1", markdown)
    text = LIST_MARKER_PATTERN.sub(r"\1", text)
    text = MARKUP_PATTERN.sub(" ", text)
    return SPACE_PATTERN.sub(" ", text).strip()


def stem(term: str) -> str | None:
    if len(term) < STEM_FROM_LENGTH:
        return None
    return term[:-STEM_TRIM]


def field_score(term: str, haystack: str, weight: int) -> int:
    if term in haystack:
        return weight
    stemmed: str | None = stem(term)
    if stemmed is not None and stemmed in haystack:
        return max(1, weight // STEM_WEIGHT_DIVISOR)
    return 0


def body_score(term: str, body: str) -> int:
    count: int = body.count(term)
    if count:
        return min(count, BODY_MATCH_CAP) * BODY_WEIGHT
    stemmed: str | None = stem(term)
    return 1 if stemmed is not None and stemmed in body else 0


def find_snippet(body: str, terms: list[str]) -> str | None:
    """About two lines of the body around the first word that matched."""

    folded: str = body.casefold()
    for term in terms:
        for needle in (term, stem(term)):
            if needle is None:
                continue
            position: int = folded.find(needle)
            if position < 0:
                continue
            start: int = max(0, position - SNIPPET_RADIUS)
            end: int = min(len(body), position + len(needle) + SNIPPET_RADIUS)
            start = body.rfind(" ", 0, start) + 1 if start > 0 else 0
            space: int = body.find(" ", end)
            end = len(body) if space < 0 else space
            prefix: str = "…" if start > 0 else ""
            suffix: str = "…" if end < len(body) else ""
            return f"{prefix}{body[start:end].strip()}{suffix}"
    return None


def score_article(article: HelpArticleRecord, terms: list[str]) -> SearchMatch | None:
    title: str = article.title.casefold()
    keywords: str = " ".join(article.keywords).casefold()
    summary: str = article.summary.casefold()
    body_text: str = plain_text(article.markdown)
    body: str = body_text.casefold()
    score: int = 0
    matched: list[str] = []
    for term in terms:
        term_score: int = (
            field_score(term, title, TITLE_WEIGHT)
            + field_score(term, keywords, KEYWORD_WEIGHT)
            + field_score(term, summary, SUMMARY_WEIGHT)
            + body_score(term, body)
        )
        if term_score:
            score += term_score
            matched.append(term)

    if not matched:
        return None

    return SearchMatch(
        article=article,
        matched_terms=len(matched),
        score=score,
        snippet=find_snippet(body_text, matched),
    )


def search_articles(
    articles: list[HelpArticleRecord], text: str, limit: int
) -> list[SearchMatch]:
    """The best matches first: most words matched, then the highest score."""

    terms: list[str] = search_terms(text)
    if not terms:
        return []

    matches: list[SearchMatch] = [
        match
        for article in articles
        if (match := score_article(article, terms)) is not None
    ]
    matches.sort(
        key=lambda match: (
            -match.matched_terms,
            -match.score,
            int(match.article.order),
            str(match.article.slug),
        )
    )
    return matches[:limit]
