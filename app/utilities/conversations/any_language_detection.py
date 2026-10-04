"""
Read the language a customer writes in, whatever it is.

1. Neutral words ("ok", "lol", "хаха"), digits, emoji and punctuation are
   set aside. Nothing left: the conversation's language is kept (then the
   contact's, then the business default).
2. The dominant script decides which languages can be meant. A script one
   language uses names it (Hebrew letters are Hebrew); Latin, Cyrillic,
   Arabic and Devanagari are shared, and their languages are scored by
   frequent words, distinctive letters and missing letters. Latin text is
   also scored as Georgian, Russian, Ukrainian, Armenian and Hebrew typed in
   Latin letters ("gamarjoba", "privet", "barev", "shalom").
3. A kept language yields only to clear evidence: at least two frequent
   words or a distinctive letter, more than the kept language has. A script
   the kept language is not written in is clear evidence by itself, except
   Latin, which every chat uses for names, brands and "ok".

Ties go to the kept language, then the business languages in their order,
then the language a script points to. The result is any BCP 47 tag; it is
a business language's own tag when the base language matches ("pt-BR").
"""

from collections.abc import Iterable
from dataclasses import dataclass

from app.schemas.dto.language_detection import DetectedLanguage
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    ScriptCode,
)
from app.utilities.conversations.language_evidence.language_evidence import (
    LanguageEvidence,
)
from app.utilities.conversations.language_evidence.language_evidence_table import (
    LANGUAGE_EVIDENCE,
)
from app.utilities.conversations.language_evidence.script_languages import (
    HAN_LANGUAGES,
    LATIN_SCRIPT,
    SHARED_SCRIPT_DEFAULTS,
    SINGLE_LANGUAGE_SCRIPTS,
    is_neutral_word,
)
from app.utilities.conversations.language_evidence.transliterated_languages import (
    TRANSLITERATED_LANGUAGE_EVIDENCE,
)
from app.utilities.conversations.language_evidence.writing_scripts import (
    COMPATIBLE_TAG_SCRIPTS,
)
from app.utilities.conversations.language_scoring import (
    HAN_SCRIPT,
    collect_script_letters,
    evidence_code,
    find_dominant_script,
    find_evidence,
    score_language,
    split_words,
)
from app.utilities.localization.language_scripts import find_likely_script_code

# Evidence needed to leave a kept language: two frequent words, or one
# distinctive letter and a word.
SWITCH_SCORE: int = 4
# What a script used by one language counts for that language.
SCRIPT_SCORE: int = 6


@dataclass(frozen=True)
class LanguageContext:
    """What is known before the text is read (technical record)."""

    version_languages: tuple[LanguageTag, ...]
    default_language: LanguageTag
    kept_language: LanguageTag | None


@dataclass(frozen=True)
class LanguageCandidate:
    """A language the text may be in, and how it would be written (technical)."""

    tag: LanguageTag
    evidence: LanguageEvidence | None
    is_transliterated: bool = False
    script_score: int = 0


def detect_any_language(text: str, context: LanguageContext) -> DetectedLanguage:
    lowered_words: list[str] = [
        word for word in split_words(text.lower()) if not is_neutral_word(word)
    ]
    readable_text: str = " ".join(lowered_words)
    script: str | None = find_dominant_script(readable_text)
    candidates: list[LanguageCandidate] = (
        [] if script is None else collect_candidates(script, context)
    )
    if script is None or not candidates:
        return keep_language(context)

    script_letters: list[str] = collect_script_letters(readable_text, script)
    scores: dict[LanguageCandidate, int] = {
        candidate: candidate.script_score
        + score_language(
            candidate.evidence, readable_text, lowered_words, script_letters
        )
        for candidate in candidates
    }
    best_score: int = max(scores.values())
    leader: LanguageCandidate = min(
        (candidate for candidate in candidates if scores[candidate] == best_score),
        key=lambda candidate: preference_rank(candidate, candidates, context, script),
    )
    kept: LanguageCandidate | None = find_candidate(context.kept_language, candidates)
    if context.kept_language is not None and (
        kept is not None or script == LATIN_SCRIPT
    ):
        kept_score: int = 0 if kept is None else scores[kept]
        if best_score >= SWITCH_SCORE and best_score > kept_score:
            return read_language(leader, best_score)

        return DetectedLanguage(
            language=context.kept_language,
            script_hint=script_hint(kept, kept_score),
            is_read_from_text=kept_score > 0 and kept_score == best_score,
        )

    if best_score > 0 or script != LATIN_SCRIPT:
        return read_language(leader, best_score)

    return DetectedLanguage(
        language=next(
            (
                language
                for language in context.version_languages
                if is_written_in(language, LATIN_SCRIPT)
            ),
            context.default_language,
        ),
        is_read_from_text=False,
    )


def keep_language(context: LanguageContext) -> DetectedLanguage:
    """Nothing to read: the kept language, else the business default."""

    return DetectedLanguage(
        language=context.kept_language or context.default_language,
        is_read_from_text=False,
    )


def read_language(candidate: LanguageCandidate, score: int) -> DetectedLanguage:
    return DetectedLanguage(
        language=candidate.tag,
        script_hint=script_hint(candidate, score),
        is_read_from_text=True,
    )


def script_hint(candidate: LanguageCandidate | None, score: int) -> ScriptCode | None:
    """Latin when the language was recognized in transliteration."""

    if candidate is None or not candidate.is_transliterated or score <= 0:
        return None

    return ScriptCode(LATIN_SCRIPT)


def collect_candidates(
    script: str,
    context: LanguageContext,
) -> list[LanguageCandidate]:
    """
    The languages a text in `script` may be in, each under the tag the
    business uses for it (the kept language's, then a version language's).
    """

    known_tags: dict[str, LanguageTag] = {}
    for language in context.version_languages:
        known_tags.setdefault(evidence_code(language), language)

    if context.kept_language is not None:
        known_tags[evidence_code(context.kept_language)] = context.kept_language

    script_tags: list[LanguageTag] = [
        tag for tag in known_tags.values() if is_written_in(tag, script)
    ]
    if script in SINGLE_LANGUAGE_SCRIPTS:
        codes: tuple[str, ...] = (
            HAN_LANGUAGES
            if script == HAN_SCRIPT
            else (SINGLE_LANGUAGE_SCRIPTS[script],)
        )
        return unique_candidates(
            LanguageCandidate(tag=tag, evidence=None, script_score=SCRIPT_SCORE)
            for tag in [
                *(known_tags.get(code, LanguageTag(code)) for code in codes),
                *script_tags,
            ]
        )

    native: list[LanguageCandidate] = [
        LanguageCandidate(
            tag=known_tags.get(code, LanguageTag(code)), evidence=evidence
        )
        for code, evidence in LANGUAGE_EVIDENCE.items()
        if evidence.script == script
    ]
    native.extend(
        LanguageCandidate(tag=tag, evidence=find_evidence(tag, script))
        for tag in script_tags
    )
    if script == LATIN_SCRIPT:
        native.extend(
            LanguageCandidate(
                tag=known_tags.get(code, LanguageTag(code)),
                evidence=evidence,
                is_transliterated=True,
            )
            for code, evidence in TRANSLITERATED_LANGUAGE_EVIDENCE.items()
        )

    return unique_candidates(native)


def unique_candidates(
    candidates: Iterable[LanguageCandidate],
) -> list[LanguageCandidate]:
    """The first candidate of each language and way of writing it."""

    unique: list[LanguageCandidate] = []
    seen: set[tuple[str, bool]] = set()
    for candidate in candidates:
        key: tuple[str, bool] = (
            evidence_code(candidate.tag),
            candidate.is_transliterated,
        )
        if key not in seen:
            seen.add(key)
            unique.append(candidate)

    return unique


def find_candidate(
    language: LanguageTag | None,
    candidates: list[LanguageCandidate],
) -> LanguageCandidate | None:
    if language is None:
        return None

    code: str = evidence_code(language)
    return next(
        (candidate for candidate in candidates if evidence_code(candidate.tag) == code),
        None,
    )


def preference_rank(
    candidate: LanguageCandidate,
    candidates: list[LanguageCandidate],
    context: LanguageContext,
    script: str,
) -> tuple[int, int]:
    """Kept language, business languages in order, the script's own, the rest."""

    code: str = evidence_code(candidate.tag)
    if context.kept_language is not None and code == evidence_code(
        context.kept_language
    ):
        return (0, 0)

    version_codes: list[str] = [
        evidence_code(language) for language in context.version_languages
    ]
    if code in version_codes:
        return (1, version_codes.index(code))

    if code in (
        SINGLE_LANGUAGE_SCRIPTS.get(script),
        SHARED_SCRIPT_DEFAULTS.get(script),
    ):
        return (2, 0)

    return (3, candidates.index(candidate))


def is_written_in(language: LanguageTag, script: str) -> bool:
    """Whether a tag's own script (CLDR likely script) is `script`."""

    return find_likely_script_code(language) in COMPATIBLE_TAG_SCRIPTS.get(
        script, frozenset({script})
    )
