from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import ChannelErrorSummary
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    EncryptedChannelSecret,
)


class ChannelDocument(BaseDocument):
    """
    A connected customer channel (concept table `channels`).

    Credentials are stored only encrypted with the platform key. When the
    platform refuses the credential the status becomes ERROR with a short
    reason and its time; the next successful delivery (or a reconnect)
    clears them.
    """

    id: ChannelId = Field(default_factory=ChannelId)
    business_id: BusinessId
    kind: ChannelKind
    external_id: ChannelExternalId | None = None
    encrypted_secret: EncryptedChannelSecret | None = None
    status: ChannelStatus = ChannelStatus.PENDING
    last_error: ChannelErrorSummary | None = None
    last_error_at: Microseconds | None = None
