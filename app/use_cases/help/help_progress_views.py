"""The person's progress as the API answers it, and an empty row to start from."""

from typed_time_provider import Microseconds

from app.schemas.domain.help_progress import HelpProgressDocument
from app.schemas.dto.help_progress import HelpProgressView
from app.schemas.typings.users.prefixed_id import UserId

# Coach marks a person may have closed; the oldest are forgotten beyond.
MAX_SEEN_COACH_MARKS: int = 64


def progress_view(progress: HelpProgressDocument | None) -> HelpProgressView:
    if progress is None:
        return HelpProgressView(seen_coach_marks=[])

    return HelpProgressView(
        seen_coach_marks=list(progress.seen_coach_marks),
        changelog_read_key=progress.changelog_read_key,
    )


def empty_progress(user_id: UserId, now: Microseconds) -> HelpProgressDocument:
    return HelpProgressDocument(user_id=user_id, created_at=now, updated_at=now)
