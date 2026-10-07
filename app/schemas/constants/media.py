"""What a customer can send besides text, and why the assistant could not read it."""

from enum import StrEnum


class AttachmentKind(StrEnum):
    """
    What a customer's message carries besides text. AUDIO (voice notes and
    audio files) is transcribed, IMAGE is shown to the model, LOCATION is
    read as coordinates; CONTACT (someone's contact card), STICKER and
    OTHER (video, documents, polls, ...) get a polite request to write.
    """

    AUDIO = "audio"
    IMAGE = "image"
    LOCATION = "location"
    CONTACT = "contact"
    STICKER = "sticker"
    OTHER = "other"


class AttachmentProblem(StrEnum):
    """
    Why the assistant could not read an attachment: a kind it does not
    read, a file over the size cap, a voice note over the length cap, a
    file the platform no longer hands out, a format that is not audio or
    an image after all, or a voice note without recognizable speech (or
    with the transcription service unavailable).
    """

    UNSUPPORTED_KIND = "unsupported_kind"
    TOO_LARGE = "too_large"
    TOO_LONG = "too_long"
    UNAVAILABLE = "unavailable"
    UNRECOGNIZED_FORMAT = "unrecognized_format"
    NOT_UNDERSTOOD = "not_understood"
