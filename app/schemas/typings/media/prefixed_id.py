"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class MessageMediaId(BasePrefixedTypedId):
    """
    Identifier of one stored file a customer sent (a voice note, a photo).

    Derived (UUID v5) from the inbox event of the message and the
    attachment's position in it, so a turn that runs again after a crash
    finds the file it stored instead of downloading it twice.
    """

    prefix = "message_media"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class WidgetUploadId(BasePrefixedTypedId):
    """
    Random identifier of one file a website chat visitor uploaded (a photo
    or a voice note) before the message that carries it was sent.
    """

    prefix = "widget_upload"


# Keep abc order for all non example types, if possible.
