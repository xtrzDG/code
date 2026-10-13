"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class AudioDurationSeconds(BaseConstrainedTypedInt):
    """Length of a voice note in whole seconds (rounded up)."""

    ge = 0


class ConcurrentUploadLimit(BaseConstrainedTypedInt):
    """
    Website chat uploads one API process takes at once
    (MEDIA_MAX_CONCURRENT_UPLOADS): each holds its file in memory while it
    is read, checked and stored, so a few never take the memory the rest
    of the API needs.
    """

    ge = 1
    le = 64


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


class UploadsPerAddressLimit(BaseConstrainedTypedInt):
    """
    Website chat uploads of one client network one API process takes at
    once: one network never holds every upload place.
    """

    ge = 1
    le = 64


class VoiceDurationLimitSeconds(BaseConstrainedTypedInt):
    """Longest voice note the platform transcribes, in seconds."""

    ge = 5
    le = 3600


# Keep abc order for all non example types, if possible.
