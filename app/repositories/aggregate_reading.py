"""
Building blocks of repository aggregations: timeline buckets and reading
grouped values back into typed choices.
"""

from enum import StrEnum

from app.repositories.document_queries import time_range
from app.schemas.dto.operations.activity_counts import ActivityPeriod
from app.schemas.dto.storage_aggregates import DocumentFieldBuckets, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFieldRange
from app.schemas.typings.insights.constrained_integers import (
    PeriodItemCount,
    TimelineSegment,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import DocumentFieldText


def period_range(
    field: DocumentFieldPath, period: ActivityPeriod
) -> DocumentFieldRange:
    """The timestamp field inside the period."""

    return time_range(field, starting_at=period.start, ending_before=period.end)


def timeline_buckets(
    field: DocumentFieldPath, period: ActivityPeriod
) -> DocumentFieldBuckets:
    """One bucket per timeline segment of the period."""

    return DocumentFieldBuckets(
        field=field,
        starts=tuple(
            DocumentFieldInteger(int(start)) for start in period.segment_starts
        ),
    )


def parse_choice[Choice: StrEnum](
    choice_type: type[Choice], value: DocumentFieldText | None
) -> Choice | None:
    """
    A grouped value as its enum member; None for a missing value or one this
    release does not know (written by a newer release during a deploy).
    """

    if value is None:
        return None

    try:
        return choice_type(str(value))
    except ValueError:
        return None


def segment_of(group: DocumentGroupCount) -> TimelineSegment:
    return TimelineSegment(0 if group.bucket is None else int(group.bucket))


def period_count(groups: list[DocumentGroupCount]) -> PeriodItemCount:
    """The count of an aggregation without groups (0 when empty)."""

    return PeriodItemCount(sum(int(group.count) for group in groups))
