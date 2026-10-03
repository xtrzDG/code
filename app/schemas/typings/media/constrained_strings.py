"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class MessageMediaType(BaseConstrainedTypedString):
    """
    Media type of a stored customer file, recognized from its bytes: audio
    or an image the model reads, e.g. "audio/ogg" or "image/jpeg".

    Example:
        media_type = MessageMediaType("image/jpeg")
    """

    min_length = 7
    max_length = 64
    pattern = r"^(audio|image)/[a-z0-9][a-z0-9.+\-]*$"


class TranscriptionModelId(BaseConstrainedTypedString):
    """
    Speech-to-text model of voice notes, e.g. "gpt-4o-transcribe".

    Example:
        model = TranscriptionModelId("gpt-4o-transcribe")
    """

    min_length = 3
    max_length = 128
    pattern = r"^[a-z0-9][a-z0-9.\-:@_]*$"


# Keep abc order for all non example types, if possible.
