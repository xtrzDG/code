import json

from app.contracts.notification_clients import WebPushClientContract
from app.contracts.notifications import PushNotificationSenderContract
from app.contracts.repositories.notification_repositories import (
    PushSubscriptionRepoContract,
)
from app.schemas.domain.outbound_messages import PushRecipient
from app.schemas.domain.push_subscriptions import PushSubscriptionDocument
from app.schemas.dto.notifications.web_push import WebPushMessage
from app.schemas.exceptions.application_errors import (
    DeliveryNotConfiguredError,
    ProviderRejectedMessageError,
)
from app.schemas.exceptions.notification_errors import PushSubscriptionGoneError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.notifications.constrained_integers import (
    PushTimeToLiveSeconds,
)
from app.schemas.typings.notifications.strings import PushPayloadJson

# A device that is off for longer gets the notification no more: by then
# the cabinet shows what happened.
TIME_TO_LIVE: PushTimeToLiveSeconds = PushTimeToLiveSeconds(24 * 60 * 60)


class PushNotificationSenderFacilitator(PushNotificationSenderContract):
    """
    Sends one device notification for the outbox worker: the payload
    {title, body, url, tag} the cabinet's service worker shows, encrypted
    for the device. A device the push service no longer knows is deleted,
    so it is not tried again; one turned off meanwhile is skipped.
    """

    def __init__(
        self,
        push_subscription_repo: PushSubscriptionRepoContract,
        web_push_client: WebPushClientContract | None,
    ) -> None:
        self._push_subscription_repo: PushSubscriptionRepoContract = (
            push_subscription_repo
        )
        self._web_push_client: WebPushClientContract | None = web_push_client

    def send(
        self,
        business_id: BusinessId,
        recipient: PushRecipient,
        body: MessageText,
    ) -> None:
        if self._web_push_client is None:
            raise DeliveryNotConfiguredError(
                "WEB_PUSH_VAPID_PUBLIC_KEY, WEB_PUSH_VAPID_PRIVATE_KEY and "
                "WEB_PUSH_VAPID_SUBJECT are not configured."
            )

        subscription: PushSubscriptionDocument | None = (
            self._push_subscription_repo.get(business_id, recipient.subscription_id)
        )
        if subscription is None:
            raise ProviderRejectedMessageError(
                "Notifications were turned off on this device."
            )

        payload: dict[str, str] = {"title": str(recipient.title), "body": str(body)}
        if recipient.url is not None:
            payload["url"] = str(recipient.url)

        if recipient.tag is not None:
            payload["tag"] = str(recipient.tag)

        try:
            self._web_push_client.send(
                WebPushMessage(
                    endpoint=subscription.endpoint,
                    p256dh=subscription.keys.p256dh,
                    auth=subscription.keys.auth,
                    payload=PushPayloadJson(json.dumps(payload, ensure_ascii=False)),
                    time_to_live_seconds=TIME_TO_LIVE,
                    urgency=recipient.urgency,
                    topic=recipient.tag,
                )
            )
        except PushSubscriptionGoneError:
            self._push_subscription_repo.delete(business_id, subscription.id)
            raise
