"""
A website chat visitor's id for the live stream, one-way from the visitor
key the widget keeps (the key itself is the visitor's credential: who
holds it may read the conversation, so it never goes into live events,
stream tickets or addresses).
"""

import hashlib
from uuid import UUID

from app.schemas.typings.channels.prefixed_id import WidgetVisitorId

VISITOR_ID_LABEL: bytes = b"assistant-workshop/widget-visitor/v1:"
UUID_BYTES: int = 16


def widget_visitor_id(visitor_key: str) -> WidgetVisitorId:
    """
    The same id for the same key (the widget's `WidgetSessionKey`, stored
    as the web chat conversation's `ChannelUserId`), never the key back.
    """

    digest: bytes = hashlib.sha256(
        VISITOR_ID_LABEL + visitor_key.encode("utf-8")
    ).digest()
    return WidgetVisitorId(UUID(bytes=digest[:UUID_BYTES]))
