"""The suppression list: customer identities a business may not message."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.privacy.strings import SuppressedIdentityText


class SuppressedIdentity(ImmutableDTO):
    """
    One way to reach a customer: their number (`channel` PHONE, an E.164
    value) or their account in a messenger (the channel's user id). The
    suppression list keeps only its digest.
    """

    channel: ChannelKind
    value: SuppressedIdentityText
