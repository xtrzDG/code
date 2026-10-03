"""The change that points a call at its archived recording."""

from collections.abc import Callable

from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.call_recordings import CallRecordingMove


def recording_moved(
    moved: CallRecordingMove,
) -> Callable[[CallDocument], CallDocument | None]:
    """
    The call with its recording at the new path, or None (nothing written)
    when it no longer points at the old one: a retention purge or a
    contact's erasure that cleared it in between wins over the archive.
    """

    def point_at_the_new_path(stored: CallDocument) -> CallDocument | None:
        if stored.recording_path != moved.from_path:
            return None

        return stored.model_copy(
            update={"recording_path": moved.to_path, "updated_at": moved.moved_at}
        )

    return point_at_the_new_path
