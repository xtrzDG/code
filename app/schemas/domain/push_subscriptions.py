from base_pydantic_schemas import BaseDocument, PersistentDocument
from typed_time_provider import Microseconds

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import (
    PushAuthSecret,
    PushEndpointUrl,
    PushPublicKey,
)
from app.schemas.typings.notifications.prefixed_id import PushSubscriptionId
from app.schemas.typings.users.prefixed_id import UserId


class PushSubscriptionKeys(PersistentDocument):
    """The browser's keys that messages to it are encrypted with (RFC 8291)."""

    p256dh: PushPublicKey
    auth: PushAuthSecret


class PushSubscriptionDocument(BaseDocument):
    """
    One browser (phone, computer) of a cabinet user that shows the
    business's notifications (Web Push), in the language the cabinet had
    when it was turned on. A push service that no longer knows the
    subscription (the user blocked notifications, the app was removed)
    ends it: the subscription is deleted.
    """

    id: PushSubscriptionId
    business_id: BusinessId
    user_id: UserId
    endpoint: PushEndpointUrl
    keys: PushSubscriptionKeys
    language: LanguageTag
    delivered_at: Microseconds | None = None
    last_error: DeliveryErrorText | None = None
