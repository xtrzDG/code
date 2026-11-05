"""The message a business's owners get when it is closed or the closure is cancelled."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.business_closures import ClosureNoticeKind
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.users.strings import UserDisplayName


class ClosureNotice(ImmutableDTO):
    """
    One owner's notice: what happened, who did it (`actor_name`; None for
    the automatic closure), when the data goes (`delete_after`, a date in
    the business's time zone) and the owner's cabinet language.
    """

    kind: ClosureNoticeKind
    business_name: BusinessName
    actor_name: UserDisplayName | None = None
    delete_after: Microseconds
    timezone: TimezoneName
    language: LanguageTag
