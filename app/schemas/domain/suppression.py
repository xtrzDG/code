from base_pydantic_schemas import BaseDocument

from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.constrained_strings import SuppressionDigest
from app.schemas.typings.privacy.prefixed_id import SuppressionEntryId


class SuppressionEntryDocument(BaseDocument):
    """
    One customer identity a business may no longer send messages the
    customer did not ask for (reminders, text-backs after a missed call,
    requests for feedback): written when the customer says STOP, removed
    when they say START.

    `identity_digest` is an HMAC-SHA256 of the identity (an E.164 number
    for `channel` PHONE, else the account id in `channel`) under the
    platform's suppression key (SUPPRESSION_LIST_KEY) and the business, so
    the entry holds nothing readable about the person and is kept when the
    customer's data is erased: a customer who said STOP is never messaged
    again, even as a new contact after an erasure. The id derives from the
    business and the digest (one entry per identity).
    """

    id: SuppressionEntryId
    business_id: BusinessId
    identity_digest: SuppressionDigest
    channel: ChannelKind
