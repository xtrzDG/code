"""
What a person has seen of the cabinet's guidance: the one-time coach
marks and the newest "What's new" entry read (GET/PUT/DELETE /v1/me/help).
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.help.constrained_strings import (
    ChangelogEntryKey,
    CoachMarkKey,
)
from app.schemas.typings.users.prefixed_id import UserId


class HelpProgressQuery(ImmutableDTO):
    user_id: UserId


class HelpProgressView(ImmutableDTO):
    """The coach marks already closed and the newest changelog entry read."""

    seen_coach_marks: list[CoachMarkKey]
    changelog_read_key: ChangelogEntryKey | None = None


class CoachMarkSeenCommand(ImmutableDTO):
    """PUT /v1/me/help/coach-marks/{key}: the person closed that hint."""

    user_id: UserId
    key: CoachMarkKey


class ChangelogReadBody(ImmutableDTO):
    """PUT /v1/me/help/changelog: the newest entry the person has read."""

    read_key: ChangelogEntryKey


class ChangelogReadCommand(ImmutableDTO):
    user_id: UserId
    body: ChangelogReadBody
