"""
How the model's grouping answer is read: topics labelled per language, the
catch-all of other questions, and how many numbered items each holds.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.schemas.constants.value import TopicKind
from app.schemas.typings.insights.constrained_strings import TopicLabel
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_flag,
    read_object,
    read_objects,
    read_strings,
    read_text,
)
from app.utilities.value.topic_grouping import CONVERSATION_PREFIX, is_known
from app.utilities.value.topic_labels import base_language, is_catch_all_label

MAX_TOPICS: int = 12
MAX_LABEL_CHARACTERS: int = 60
JSON_OBJECT: re.Pattern[str] = re.compile(r"\{.*\}", re.DOTALL)
LABEL_QUOTES: str = "\"'«»“”„`"
OTHER_KEY: str = "\u0000other"


@dataclass(frozen=True)
class GroupedTopic:
    """
    One topic the model returned: named (its labels by base language, the
    first label language first) or the catch-all, with how many items of
    each kind it holds.
    """

    kind: TopicKind
    labels: tuple[tuple[str, TopicLabel], ...]
    conversation_count: int
    question_count: int


def read_grouped_topics(
    answer: str | None,
    conversation_total: int,
    question_total: int,
    label_languages: Sequence[str],
) -> list[GroupedTopic] | None:
    """
    The topics of the answer, most conversations first (then most open
    questions, then by label) and the catch-all last, at most MAX_TOPICS:
    each item counted once (in the first topic naming it), unknown items
    ignored, topics of the same first label merged (every catch-all into
    one), empty ones left out. Labels only in the requested languages; a
    topic named only like a catch-all is the catch-all. None: the answer is
    not a JSON object with a `topics` list.
    """

    parsed: JsonObject | None = read_answer_object(answer)
    if parsed is None or not isinstance(parsed.get("topics"), list):
        return None

    languages: list[str] = [base_language(language) for language in label_languages]
    seen: set[str] = set()
    counts: dict[str, list[int]] = {}
    named: dict[str, dict[str, TopicLabel]] = {}
    for topic in read_objects(parsed, "topics"):
        labels: dict[str, TopicLabel] = read_labels(topic, languages)
        key: str | None = topic_key(topic, labels)
        if key is None:
            continue

        if key != OTHER_KEY:
            merged: dict[str, TopicLabel] = named.setdefault(key, {})
            for language, label in labels.items():
                merged.setdefault(language, label)
        tally: list[int] = counts.setdefault(key, [0, 0])
        for item in read_strings(topic, "items"):
            name: str = item.strip().upper()
            if name in seen or not is_known(name, conversation_total, question_total):
                continue

            seen.add(name)
            tally[0 if name.startswith(CONVERSATION_PREFIX) else 1] += 1

    grouped: list[GroupedTopic] = [
        GroupedTopic(
            kind=TopicKind.NAMED,
            labels=tuple(
                (language, named[key][language])
                for language in languages
                if language in named[key]
            ),
            conversation_count=conversations,
            question_count=questions,
        )
        for key, (conversations, questions) in counts.items()
        if key != OTHER_KEY and (conversations or questions)
    ]
    grouped.sort(
        key=lambda topic: (
            -topic.conversation_count,
            -topic.question_count,
            str(topic.labels[0][1]).casefold(),
        )
    )
    other: list[int] = counts.get(OTHER_KEY, [0, 0])
    kept: list[GroupedTopic] = grouped[: MAX_TOPICS - (1 if any(other) else 0)]
    if any(other):
        kept.append(GroupedTopic(TopicKind.OTHER, (), other[0], other[1]))

    return kept


def read_labels(topic: JsonObject, languages: Sequence[str]) -> dict[str, TopicLabel]:
    """
    The topic's labels in the requested languages: `labels` by language,
    else (the answer of a model that names one label) `label` as the first
    language's.
    """

    labels: dict[str, TopicLabel] = {}
    by_language: JsonObject | None = read_object(topic, "labels")
    if by_language is not None:
        for raw_language in by_language:
            language: str = base_language(raw_language)
            label: TopicLabel | None = clean_label(read_text(by_language, raw_language))
            if language in languages and label is not None:
                labels.setdefault(language, label)

    single: TopicLabel | None = clean_label(read_text(topic, "label"))
    if not labels and single is not None and languages:
        labels[languages[0]] = single

    return {language: labels[language] for language in languages if language in labels}


def topic_key(topic: JsonObject, labels: dict[str, TopicLabel]) -> str | None:
    """
    The catch-all's key, else that of the label in the first language it
    has (`labels` is in the order of the languages; None: no label at all).
    """

    if read_flag(topic, "other") or (
        labels and all(is_catch_all_label(str(label)) for label in labels.values())
    ):
        return OTHER_KEY

    if not labels:
        return None

    return str(next(iter(labels.values()))).casefold()


def read_answer_object(answer: str | None) -> JsonObject | None:
    if answer is None:
        return None

    match: re.Match[str] | None = JSON_OBJECT.search(answer)
    return None if match is None else parse_json_object(match.group(0))


def clean_label(text: str | None) -> TopicLabel | None:
    """A label on one line without quotes, at most MAX_LABEL_CHARACTERS."""

    if text is None:
        return None

    label: str = " ".join(text.strip(LABEL_QUOTES + " ").split())
    if not label:
        return None

    return TopicLabel(label[:MAX_LABEL_CHARACTERS].rstrip())
