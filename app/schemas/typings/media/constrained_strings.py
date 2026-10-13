"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class DeclaredMediaType(BaseConstrainedTypedString):
    """
    Media type a website visitor's browser declared for an upload, read
    from its `DeclaredUploadType`: lower case, without its parameters
    ("audio/webm;codecs=opus" -> "audio/webm"). Still only a claim: the
    file's own bytes must say the same type.

    Example:
        declared = DeclaredMediaType("audio/webm")
    """

    min_length = 3
    max_length = 127
    pattern = r"^[a-z0-9][a-z0-9!#$&^_.+\-]*/[a-z0-9][a-z0-9!#$&^_.+\-]*$"


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
