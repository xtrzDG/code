"""
The keywords of Instagram comment-to-DM: kept once each (letter case does
not count), and found in a comment as whole words or phrases in any case.
"""

import re
import unicodedata

from app.schemas.typings.meta_connection.constrained_strings import (
    CommentTriggerKeyword,
)


def distinct_keywords(
    keywords: list[CommentTriggerKeyword],
) -> list[CommentTriggerKeyword]:
    """The keywords in their order, each once (compared without case)."""

    seen: set[str] = set()
    kept: list[CommentTriggerKeyword] = []
    for keyword in keywords:
        folded: str = fold(str(keyword))
        if folded not in seen:
            seen.add(folded)
            kept.append(keyword)

    return kept


def matching_keyword(
    comment: str, keywords: list[CommentTriggerKeyword]
) -> CommentTriggerKeyword | None:
    """
    The first keyword the comment holds as a word or phrase of its own
    ("menu" in "Menu please!", not in "menus" or "#menu2"), compared
    without letter case and in Unicode's compatibility form, so "МЕНЮ" and
    "меню" and full-width letters match; None when it holds none.
    """

    folded_comment: str = fold(comment)
    for keyword in keywords:
        pattern: str = r"(?<!\w)" + re.escape(fold(str(keyword))) + r"(?!\w)"
        if re.search(pattern, folded_comment) is not None:
            return keyword

    return None


def fold(text: str) -> str:
    """Compatibility-normalized, case-folded, inner blanks made single."""

    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())
