"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class AudioDurationSeconds(BaseConstrainedTypedInt):
    """Length of a voice note in whole seconds (rounded up)."""

    ge = 0


class DeletedMediaCount(BaseConstrainedTypedInt):
    """How many stored customer files one purge removed."""

    ge = 0


class MediaByteCount(BaseConstrainedTypedInt):
    """Size of a customer file in bytes."""

    ge = 0


class MediaByteLimit(BaseConstrainedTypedInt):
    """
    Largest customer file of one kind the platform downloads, in bytes (at
    most 25 MiB: the transcription service's own limit).
    """

    ge = 1024
    le = 25 * 1024 * 1024


class VoiceDurationLimitSeconds(BaseConstrainedTypedInt):
    """Longest voice note the platform transcribes, in seconds."""

    ge = 5
    le = 3600


# Keep abc order for all non example types, if possible.
