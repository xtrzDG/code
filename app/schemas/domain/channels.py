from base_pydantic_schemas import BaseDocument
from pydantic import Field

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    EncryptedChannelSecret,
)


class ChannelDocument(BaseDocument):
    """
    A connected customer channel (concept table `channels`).

    Credentials are stored only encrypted with the platform key.
    """

    id: ChannelId = Field(default_factory=ChannelId)
    business_id: BusinessId
    kind: ChannelKind
    external_id: ChannelExternalId | None = None
    encrypted_secret: EncryptedChannelSecret | None = None
    status: ChannelStatus = ChannelStatus.PENDING
