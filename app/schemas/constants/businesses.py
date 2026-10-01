from enum import IntEnum, StrEnum


class BusinessStatus(StrEnum):
    """Lifecycle of a business assistant from questionnaire to launch."""

    DRAFT = "draft"
    QUESTIONNAIRE_SUBMITTED = "questionnaire_submitted"
    ASSEMBLED = "assembled"
    READY_FOR_REVIEW = "ready_for_review"
    LIVE = "live"
    PAUSED = "paused"


class Weekday(IntEnum):
    """ISO weekday number (Monday is 1)."""

    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7
