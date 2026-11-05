"""
How well a name the customer wrote matches a stored name, in any script.

Both names are compared as written and spelled in Latin letters
(`name_spellings`), word by word with the knowledge search's token
similarity (inflection, one typo): "Нино" finds "Nino Beridze", "стрижку"
finds "Стрижка", "ნინო" finds "Nino". Hebrew and Arabic names, written
without vowels, also match by their consonants. The score mixes how much
of the asked name is found (most) and how much of the stored name is
covered, so "Nino" prefers the master "Nino" to "Nino Beridze".
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.utilities.bookings.name_spellings import (
    consonant_skeleton,
    is_abjad_text,
    spell_name_in_latin,
)
from app.utilities.knowledge.ranking.token_similarity import weighted_coverage
from app.utilities.knowledge.search_text import (
    SearchToken,
    fold_words,
    tokenize,
    unique_tokens,
)

EXACT_NAME_SCORE: float = 1.0
# Below this a stored name is not what the customer meant.
NAME_MATCH_THRESHOLD: float = 0.5
QUERY_COVERAGE_SHARE: float = 0.8
CONSONANT_MATCH_SCORE: float = 0.6
MIN_SKELETON_LENGTH: int = 2
# Best matches closer than this to each other are equally likely.
AMBIGUITY_MARGIN: float = 0.1


@dataclass(frozen=True)
class NameMatch[Item]:
    """One stored name that matches, with its score in (0, 1]."""

    item: Item
    score: float


def name_match_score(query: str, name: str) -> float:
    """How well `name` matches the asked `query`, in [0, 1] (see the module)."""

    if fold_words(query) == "" or fold_words(name) == "":
        return 0.0

    query_forms: list[str] = [query, spell_name_in_latin(query)]
    name_forms: list[str] = [name, spell_name_in_latin(name)]
    if any(
        fold_words(query_form) == fold_words(name_form)
        for query_form in query_forms
        for name_form in name_forms
    ):
        return EXACT_NAME_SCORE

    cache: dict[tuple[str, str], float] = {}
    best: float = max(
        coverage_score(unique_tokens(tokenize(query_form)), name_form, cache)
        for query_form in query_forms
        for name_form in name_forms
    )
    if best < NAME_MATCH_THRESHOLD and is_abjad_text(query):
        best = max(best, skeleton_score(query_forms[1], name_forms[1]))

    return best


def coverage_score(
    query_tokens: list[SearchToken],
    name: str,
    cache: dict[tuple[str, str], float],
) -> float:
    name_tokens: list[SearchToken] = unique_tokens(tokenize(name))
    if not query_tokens or not name_tokens:
        return 0.0

    query_coverage: float = weighted_coverage(query_tokens, name_tokens, cache)
    name_coverage: float = weighted_coverage(name_tokens, query_tokens, cache)
    return (
        QUERY_COVERAGE_SHARE * query_coverage
        + (1.0 - QUERY_COVERAGE_SHARE) * name_coverage
    )


def skeleton_score(latin_query: str, latin_name: str) -> float:
    """Every asked word's consonants equal those of a stored word."""

    name_skeletons: set[str] = {
        consonant_skeleton(word) for word in latin_name.split(" ")
    }
    query_skeletons: list[str] = [
        consonant_skeleton(word) for word in latin_query.split(" ")
    ]
    if any(len(skeleton) < MIN_SKELETON_LENGTH for skeleton in query_skeletons):
        return 0.0

    if all(skeleton in name_skeletons for skeleton in query_skeletons):
        return CONSONANT_MATCH_SCORE

    return 0.0


def best_name_matches[Item](
    query: str,
    named_items: Sequence[tuple[Item, str]],
) -> list[NameMatch[Item]]:
    """
    The items whose name matches best: one item, several equally likely
    ones (the customer has to choose), or none.
    """

    matches: list[NameMatch[Item]] = [
        NameMatch(item=item, score=score)
        for item, name in named_items
        if (score := name_match_score(query, name)) >= NAME_MATCH_THRESHOLD
    ]
    if not matches:
        return []

    top: float = max(match.score for match in matches)
    if top >= EXACT_NAME_SCORE:
        return [match for match in matches if match.score >= EXACT_NAME_SCORE]

    return [match for match in matches if match.score > top - AMBIGUITY_MARGIN]
