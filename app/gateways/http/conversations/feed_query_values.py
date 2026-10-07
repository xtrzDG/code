"""
Query parameters of the conversation feed as typed values: empty means
absent, an unknown or malformed value is a validation error.
"""

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.conversations.booleans import IncludeSandboxConversations
from app.schemas.typings.conversations.constrained_strings import ConversationSearchText

TRUE_FLAGS: frozenset[str] = frozenset({"1", "true", "yes"})
FALSE_FLAGS: frozenset[str] = frozenset({"0", "false", "no"})


def parse_channel(raw_channel: str | None) -> ChannelKind | None:
    if raw_channel is None or raw_channel.strip() == "":
        return None

    try:
        return ChannelKind(raw_channel.strip().lower())
    except ValueError as error:
        known_channels: str = ", ".join(kind.value for kind in ChannelKind)
        raise ValidationFailedError(
            f"channel must be one of: {known_channels}."
        ) from error


def parse_status(raw_status: str | None) -> ConversationStatus | None:
    if raw_status is None or raw_status.strip() == "":
        return None

    try:
        return ConversationStatus(raw_status.strip().lower())
    except ValueError as error:
        known_statuses: str = ", ".join(status.value for status in ConversationStatus)
        raise ValidationFailedError(
            f"status must be one of: {known_statuses}."
        ) from error


def parse_local_date(raw_date: str | None, name: str) -> LocalDate | None:
    if raw_date is None or raw_date.strip() == "":
        return None

    try:
        return LocalDate(raw_date.strip())
    except (ValueError, TypeError) as error:
        raise ValidationFailedError(
            f"{name} must be a date like 2026-10-01."
        ) from error


def parse_search(raw_search: str | None) -> ConversationSearchText | None:
    if raw_search is None or raw_search.strip() == "":
        return None

    try:
        return ConversationSearchText(raw_search.strip())
    except (ValueError, TypeError) as error:
        raise ValidationFailedError(
            f"search may be at most {ConversationSearchText.max_length} characters."
        ) from error


def parse_include_sandbox(raw_flag: str | None) -> IncludeSandboxConversations:
    if raw_flag is None:
        return False

    flag: str = raw_flag.strip().lower()
    if flag in TRUE_FLAGS:
        return True

    if flag in FALSE_FLAGS:
        return False

    raise ValidationFailedError("include_sandbox must be true or false.")
