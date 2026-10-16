"""What the Web Push client sends: one encrypted message to one device."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.notifications import WebPushUrgency
from app.schemas.typings.notifications.constrained_integers import (
    PushTimeToLiveSeconds,
)
from app.schemas.typings.notifications.constrained_strings import (
    PushAuthSecret,
    PushEndpointUrl,
    PushNotificationTag,
    PushPublicKey,
)
from app.schemas.typings.notifications.strings import PushPayloadJson


class WebPushMessage(ImmutableDTO):
    """
    One notification for one browser subscription: the payload is
    encrypted for the browser's keys (RFC 8291). `time_to_live_seconds`
    bounds how long the push service keeps it for an offline device; a
    newer message with the same `topic` replaces one still waiting there.
    """

    endpoint: PushEndpointUrl
    p256dh: PushPublicKey
    auth: PushAuthSecret
    payload: PushPayloadJson
    time_to_live_seconds: PushTimeToLiveSeconds
    urgency: WebPushUrgency = WebPushUrgency.NORMAL
    topic: PushNotificationTag | None = None
