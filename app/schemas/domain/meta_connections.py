from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.meta_connection import MetaConnectionPurpose
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.schemas.typings.meta_connection.booleans import IsMetaConnectionStateConsumed
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaConnectionStateHash,
)
from app.schemas.typings.meta_connection.prefixed_id import MetaConnectionStateId
from app.schemas.typings.users.prefixed_id import UserId


class MetaConnectionStateDocument(BaseDocument):
    """
    A Facebook sign-in an owner started in the cabinet (migration 1212), as
    Google Calendar's consent is: the random state the cabinet carries
    through Meta's window is stored only as its hash (`state_hash`, the
    document's key), belongs to the owner and business that started it and
    to one purpose (WhatsApp Embedded Signup or the page picker), and ends
    after fifteen minutes.

    Meta's code is exchanged once: `is_consumed` is set before the
    exchange, so a sign-in cannot be finished twice. The page picker keeps
    the owner's token from the exchange (`encrypted_user_token`, encrypted
    with the platform key) until it ends, to read the token of the page the
    owner chooses; WhatsApp keeps nothing (the business's token goes to its
    channel).
    """

    id: MetaConnectionStateId = Field(default_factory=MetaConnectionStateId)
    business_id: BusinessId
    user_id: UserId
    purpose: MetaConnectionPurpose
    state_hash: MetaConnectionStateHash
    expires_at: Microseconds
    is_consumed: IsMetaConnectionStateConsumed = False
    encrypted_user_token: EncryptedChannelSecret | None = Field(
        default=None, repr=False
    )
