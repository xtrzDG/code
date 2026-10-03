"""
What a row of the fact table is about, in typed terms an owner's cabinet
can put into words: its area, the named field, weekday or link, the date
of a special day, or the owner's own title of an item, resource or niche
question.

The rows are the ones BusinessFactsTransformer writes; their keys and
labels are matched here, so the two stay in step.
"""

import re
from collections.abc import Mapping

from app.schemas.constants.businesses import BusinessLinkKind, Weekday
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.setup import (
    PendingChangeAction,
    PendingChangeArea,
    PendingChangeField,
)
from app.schemas.domain.assistants import BusinessFact
from app.schemas.dto.setup.pending_changes import PendingChange
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.setup.strings import PendingChangeSubject

LABEL_SEPARATOR: str = ": "
HOURS_KEY_PREFIX: str = "hours_"
SPECIAL_DAY_KEY_PREFIX: str = "special_day_"
LINK_KEY_PREFIX: str = "link_"
RESOURCE_KEY_PATTERN: re.Pattern[str] = re.compile(r"^resource_\d+$")
SPECIAL_DAY_KEY_PATTERN: re.Pattern[str] = re.compile(r"^special_day_\d+$")
KNOWLEDGE_KEY_PATTERN: re.Pattern[str] = re.compile(
    "^(" + "|".join(kind.value for kind in KnowledgeItemKind) + r")_\d+$"
)
ISO_DATE_PATTERN: re.Pattern[str] = re.compile(r"\d{4}-\d{2}-\d{2}$")
QUESTION_KINDS: frozenset[KnowledgeItemKind] = frozenset(
    {KnowledgeItemKind.FAQ, KnowledgeItemKind.POLICY}
)
PROFILE_FIELDS: frozenset[PendingChangeField] = frozenset(
    {
        PendingChangeField.BUSINESS_NAME,
        PendingChangeField.BUSINESS_TYPE,
        PendingChangeField.CITY,
        PendingChangeField.COUNTRY,
        PendingChangeField.ADDRESS,
        PendingChangeField.MAPS_LINK,
        PendingChangeField.PUBLIC_PHONE,
        PendingChangeField.TIME_ZONE,
    }
)
LANGUAGE_FIELDS: frozenset[PendingChangeField] = frozenset(
    {PendingChangeField.LANGUAGES, PendingChangeField.DEFAULT_LANGUAGE}
)
WEEKDAYS_BY_KEY: dict[str, Weekday] = {
    f"{HOURS_KEY_PREFIX}{weekday.name.lower()}": weekday for weekday in Weekday
}
LINK_KINDS_BY_KEY: dict[str, BusinessLinkKind] = {
    f"{LINK_KEY_PREFIX}{kind.value}": kind for kind in BusinessLinkKind
}
FIELDS_BY_KEY: dict[str, PendingChangeField] = {
    field.value: field for field in PendingChangeField
}


def is_matched_by_label(key: str) -> bool:
    """
    Rows numbered in their list (items, resources, special days) are told
    apart by their label: a new item renumbers the ones after it.
    """

    return bool(
        KNOWLEDGE_KEY_PATTERN.match(key)
        or RESOURCE_KEY_PATTERN.match(key)
        or SPECIAL_DAY_KEY_PATTERN.match(key)
    )


def read_special_day(fact: BusinessFact) -> LocalDate | None:
    """The date of a special-day row ("Special day 2026-12-31")."""

    if not SPECIAL_DAY_KEY_PATTERN.match(str(fact.key)):
        return None

    match: re.Match[str] | None = ISO_DATE_PATTERN.search(str(fact.label))
    return None if match is None else LocalDate(match.group(0))


def describe_fact_change(
    fact: BusinessFact,
    action: PendingChangeAction,
    answer_labels: Mapping[str, str],
) -> PendingChange:
    """
    The change of one row: its area and what it is about. A row the table
    builder writes under a niche question's own key is a niche ANSWERS
    row, named by `answer_labels` (fact key -> the question in the owner's
    language) or else by its English label.
    """

    key: str = str(fact.key)
    knowledge_match: re.Match[str] | None = KNOWLEDGE_KEY_PATTERN.match(key)
    if knowledge_match is not None:
        kind = KnowledgeItemKind(knowledge_match.group(1))
        return PendingChange(
            area=(
                PendingChangeArea.QUESTIONS
                if kind in QUESTION_KINDS
                else PendingChangeArea.OFFER
            ),
            action=action,
            item_kind=kind,
            subject=label_subject(fact),
        )

    if RESOURCE_KEY_PATTERN.match(key):
        return PendingChange(
            area=PendingChangeArea.RESOURCES,
            action=action,
            subject=label_subject(fact),
        )

    if SPECIAL_DAY_KEY_PATTERN.match(key):
        return PendingChange(
            area=PendingChangeArea.SPECIAL_DAYS,
            action=action,
            date=read_special_day(fact),
        )

    if key in WEEKDAYS_BY_KEY:
        return PendingChange(
            area=PendingChangeArea.HOURS, action=action, weekday=WEEKDAYS_BY_KEY[key]
        )

    if key in LINK_KINDS_BY_KEY:
        return PendingChange(
            area=PendingChangeArea.LINKS,
            action=action,
            link_kind=LINK_KINDS_BY_KEY[key],
        )

    field: PendingChangeField | None = FIELDS_BY_KEY.get(key)
    if field is not None:
        return PendingChange(area=field_area(field), action=action, field=field)

    return PendingChange(
        area=PendingChangeArea.ANSWERS,
        action=action,
        subject=PendingChangeSubject(answer_labels.get(key) or str(fact.label)),
    )


def field_area(field: PendingChangeField) -> PendingChangeArea:
    if field in PROFILE_FIELDS:
        return PendingChangeArea.PROFILE

    if field in LANGUAGE_FIELDS:
        return PendingChangeArea.LANGUAGES

    return PendingChangeArea.BOOKING_RULES


def label_subject(fact: BusinessFact) -> PendingChangeSubject:
    """ "Menu item: Khachapuri" -> "Khachapuri" (the owner's own title)."""

    label: str = str(fact.label)
    _, separator, title = label.partition(LABEL_SEPARATOR)
    return PendingChangeSubject(title.strip() if separator else label)
