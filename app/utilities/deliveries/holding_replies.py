"""The identity of the one "one moment" a slow reply sends."""

import hashlib
from uuid import UUID

from app.schemas.typings.conversations.prefixed_id import MessageId

# Fixed namespace (never change it: a turn that runs again must find the
# holding message it already sent).
HOLDING_MESSAGE_NAMESPACE: UUID = UUID("6bc6054a-1cf3-4277-864d-85cebefc0664")
UUID_BYTES: int = 16


def derive_holding_message_id(reply_message_id: MessageId) -> MessageId:
    """
    One holding message per reply: the same reply, the same id (message
    ids are version-4 UUIDs, so the digest takes that shape).
    """

    digest: bytes = hashlib.sha256(
        f"{HOLDING_MESSAGE_NAMESPACE}|holding|{reply_message_id}".encode()
    ).digest()
    return MessageId(UUID(bytes=digest[:UUID_BYTES], version=4))
