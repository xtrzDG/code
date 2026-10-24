"""
Upcasters of the stored conversation topics (`document_upgrades` registers
them).

Version 2 gives every topic a `kind` and its `labels` per language. A
version 1 row has one label per topic, written in the business owner's
language (`label_language`): it becomes the topic's only entry in
`labels`, and a label naming the catch-all ("Другие вопросы", "Other
questions", ...) makes the topic OTHER, which every cabinet names itself.
"""

from typing import cast

from app.schemas.constants.value import TopicKind
from app.utilities.value.topic_labels import is_catch_all_label

# Stored JSON of one document, before validation (the storage boundary).
type StoredJsonObject = dict[str, object]

LABEL_LANGUAGE_FIELD_NAME: str = "label_language"
GROUPS_FIELD_NAME: str = "groups"
TOPICS_FIELD_NAME: str = "topics"


def upgrade_conversation_topics_from_v1(
    document: StoredJsonObject,
) -> StoredJsonObject:
    """Each topic's one label as its owner-language label, the catch-all OTHER."""

    language: object = document.get(LABEL_LANGUAGE_FIELD_NAME)
    groups: object = document.get(GROUPS_FIELD_NAME)
    if not isinstance(language, str) or not isinstance(groups, list):
        return document

    upgraded: StoredJsonObject = dict(document)
    upgraded[GROUPS_FIELD_NAME] = [
        _upgrade_group(group, language) for group in cast(list[object], groups)
    ]
    return upgraded


def _upgrade_group(group: object, language: str) -> object:
    if not isinstance(group, dict):
        return group

    stored: StoredJsonObject = cast(StoredJsonObject, group)
    topics: object = stored.get(TOPICS_FIELD_NAME)
    if not isinstance(topics, list):
        return stored

    upgraded: StoredJsonObject = dict(stored)
    upgraded[TOPICS_FIELD_NAME] = [
        _upgrade_topic(topic, language) for topic in cast(list[object], topics)
    ]
    return upgraded


def _upgrade_topic(topic: object, language: str) -> object:
    if not isinstance(topic, dict):
        return topic

    stored: StoredJsonObject = cast(StoredJsonObject, topic)
    label: object = stored.get("label")
    if not isinstance(label, str) or "labels" in stored:
        return stored

    upgraded: StoredJsonObject = dict(stored)
    upgraded["labels"] = [{"language": language, "label": label}]
    upgraded["kind"] = (
        TopicKind.OTHER.value if is_catch_all_label(label) else TopicKind.NAMED.value
    )
    return upgraded
