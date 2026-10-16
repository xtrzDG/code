from base_pydantic_schemas import BaseDocument
from pydantic import Field

from app.schemas.typings.help.constrained_strings import (
    ChangelogEntryKey,
    CoachMarkKey,
)
from app.schemas.typings.users.prefixed_id import UserId


class HelpProgressDocument(BaseDocument):
    """
    What one person has already seen of the cabinet's guidance (a
    platform collection, stored under the user's id): the one-time coach
    marks they closed and the newest "What's new" entry they read, so
    neither comes back on another device. Account deletion removes it with
    the account.
    """

    user_id: UserId
    seen_coach_marks: list[CoachMarkKey] = Field(default_factory=list[CoachMarkKey])
    changelog_read_key: ChangelogEntryKey | None = None
