"""
Rules for what a booking of an offer takes and costs (knowledge items of
kind SERVICE, PACKAGE and ROOM_TYPE):

- only services and packages have a buffer after them (a room type is
  booked by the night, with check-in and check-out times instead);
- only bookable offers have performers;
- only room types have seasonal nightly rates, at most 24 seasons that
  never overlap (a night has exactly one rate).
"""

from collections.abc import Sequence

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.knowledge import SeasonalNightlyRate
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.knowledge.constrained_integers import BufferMinutes

MAX_SEASONS: int = 24
BUFFER_KINDS: frozenset[KnowledgeItemKind] = frozenset(
    {KnowledgeItemKind.SERVICE, KnowledgeItemKind.PACKAGE}
)
PERFORMED_KINDS: frozenset[KnowledgeItemKind] = frozenset(
    {KnowledgeItemKind.SERVICE, KnowledgeItemKind.PACKAGE, KnowledgeItemKind.ROOM_TYPE}
)
# Every month and day of a leap year, as "MM-DD" (seasons repeat yearly).
DAYS_IN_MONTH: tuple[int, ...] = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
YEAR_DAYS: tuple[str, ...] = tuple(
    f"{month:02d}-{day:02d}"
    for month, days in enumerate(DAYS_IN_MONTH, start=1)
    for day in range(1, days + 1)
)


def check_buffer(
    kind: KnowledgeItemKind,
    buffer_minutes: BufferMinutes | None,
) -> BufferMinutes | None:
    if buffer_minutes is None or int(buffer_minutes) == 0:
        return None

    if kind not in BUFFER_KINDS:
        raise ValidationFailedError(
            "Only services and packages have a break after them."
        )

    return buffer_minutes


def check_performers_allowed(
    kind: KnowledgeItemKind,
    performer_ids: Sequence[ResourceId],
) -> list[ResourceId]:
    if performer_ids and kind not in PERFORMED_KINDS:
        raise ValidationFailedError(
            "Only services, packages and room types are performed by resources."
        )

    return list(dict.fromkeys(performer_ids))


def check_seasonal_rates(
    kind: KnowledgeItemKind,
    seasons: Sequence[SeasonalNightlyRate],
) -> list[SeasonalNightlyRate]:
    """
    The seasons as given, for a room type, without overlaps.

    Raises:
        ValidationFailedError: not a room type, too many seasons, or two
            seasons share a day.
    """

    if not seasons:
        return []

    if kind is not KnowledgeItemKind.ROOM_TYPE:
        raise ValidationFailedError("Only room types have seasonal nightly rates.")

    if len(seasons) > MAX_SEASONS:
        raise ValidationFailedError(f"A room type has at most {MAX_SEASONS} seasons.")

    taken: dict[str, int] = {}
    for index, season in enumerate(seasons):
        for day in season_days(season):
            if day in taken:
                raise ValidationFailedError(
                    f"Seasons {taken[day] + 1} and {index + 1} both include {day}; "
                    "a night must have one rate."
                )

            taken[day] = index

    return [season.model_copy() for season in seasons]


def season_days(season: SeasonalNightlyRate) -> list[str]:
    """Every "MM-DD" of the season (over New Year when it ends first)."""

    starts: str = str(season.starts_on)
    ends: str = str(season.ends_on)
    if starts <= ends:
        return [day for day in YEAR_DAYS if starts <= day <= ends]

    return [day for day in YEAR_DAYS if day >= starts or day <= ends]
