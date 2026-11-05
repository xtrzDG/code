"""
Records of business B for the notification operations of the matrix: a
staff contact's key, a device of B's owner and a signed link.
"""

from typing import Any, cast

from typed_time_provider import Microseconds

from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.domain.push_subscriptions import (
    PushSubscriptionDocument,
    PushSubscriptionKeys,
)
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import (
    PushAuthSecret,
    PushEndpointUrl,
    PushPublicKey,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.notifications.staff_delivery_keys import push_subscription_id
from tests.e2e.harness import Workshop

type JsonObject = dict[str, Any]

B: str = "/v1/businesses/{business_id}"

# The example keys of RFC 8291 (appendix A): a real P-256 point and secret.
DEVICE_P256DH: str = (
    "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-"
    "AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4"
)
DEVICE_AUTH: str = "BTBZMqHH6r4Tts7J_aSIgg"
DEVICE_ENDPOINT: str = "https://fcm.googleapis.com/fcm/send/authorization-matrix"
# Far beyond any test run (2100-01-01).
LINK_EXPIRY: Microseconds = Microseconds(4_102_444_800_000_000)
NOTIFICATION_BODIES: dict[str, JsonObject] = {
    f"PUT {B}/notification-preferences": {"events": ["handoff"]},
    f"POST {B}/push-subscriptions": {
        "endpoint": DEVICE_ENDPOINT,
        "keys": {"p256dh": DEVICE_P256DH, "auth": DEVICE_AUTH},
        "language": "en",
    },
}


def notification_path_values(
    workshop: Workshop,
    storage_scope: Any,
    business_id: str,
    owner_headers: dict[str, str],
) -> dict[str, str]:
    """contact_key, subscription_id and token of business B."""

    client = workshop.client
    base = f"/v1/businesses/{business_id}"
    contacts = client.get(f"{base}/notification-contacts", headers=owner_headers)
    owner_id = UserId(
        str(client.get("/v1/me", headers=owner_headers).json()["user"]["id"])
    )
    business = BusinessId(business_id)
    device = PushSubscriptionDocument(
        id=push_subscription_id(business, owner_id, DEVICE_ENDPOINT),
        business_id=business,
        user_id=owner_id,
        endpoint=PushEndpointUrl(DEVICE_ENDPOINT),
        keys=PushSubscriptionKeys(
            p256dh=PushPublicKey(DEVICE_P256DH), auth=PushAuthSecret(DEVICE_AUTH)
        ),
        language=LanguageTag("en"),
    )
    container = workshop.container
    with storage_scope.scoped_to_business(business):
        container.repositories.push_subscription_repo().save(device)

    token = container.facilitators.staff_link_signer().sign(
        StaffLinkClaims(
            business_id=business,
            target=StaffLinkTarget.NOTIFICATIONS,
            expires_at=LINK_EXPIRY,
        )
    )
    items = cast(list[JsonObject], contacts.json()["items"])
    return {
        "contact_key": str(items[0]["key"]),
        "subscription_id": str(device.id),
        "token": str(token),
    }
