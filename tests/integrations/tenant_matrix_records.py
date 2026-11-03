"""
Another business's records for the public API's cross-tenant matrix
(AUTHZ-02): a booking with its contact, a lead, a conversation and a
webhook subscription, each made the way that business would make it, and
the request bodies that name them.
"""

from dataclasses import dataclass
from typing import Any

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.integrations.integration_shop import IntegrationShop

THEIR_CONTACT_NAME: str = "Zurab"


@dataclass(frozen=True)
class TheirRecords:
    """What business B holds; every value is an id or a name of B."""

    business_id: str
    booking_id: str
    contact_id: str
    lead_id: str
    conversation_id: str
    webhook_id: str
    resource_id: str
    # B's own key: B reads its records back with it after the matrix.
    key: str

    def path_ids(self) -> dict[str, str]:
        """B's object id for each path parameter of the public API."""

        return {
            "booking_id": self.booking_id,
            "contact_id": self.contact_id,
            "lead_id": self.lead_id,
            "conversation_id": self.conversation_id,
            "webhook_id": self.webhook_id,
        }

    def markers(self) -> set[str]:
        """Strings that must never appear in an answer to another business."""

        return {*self.path_ids().values(), self.business_id, self.resource_id}

    def bodies(self) -> dict[tuple[str, str], dict[str, Any]]:
        """
        A body for each operation that takes one, naming B's records
        wherever the body can name a record.
        """

        return {
            ("POST", "/v1/public-api/bookings"): {
                "contact_name": "Ana",
                "date": "2026-10-06",
                "time": "14:00",
                "party_size": 2,
                "resource_id": self.resource_id,
            },
            ("POST", "/v1/public-api/leads"): {
                "contact_name": "Ana",
                "type": "banquet",
                "details": "Birthday for 20",
            },
            ("POST", "/v1/public-api/webhooks"): {
                "url": "https://hooks.zapier.com/hooks/catch/1/abc",
                "event_types": ["lead.created"],
            },
        }


def store_conversation(shop: IntegrationShop) -> str:
    """A website chat of the shop's business, stored as the inbox stores one."""

    container = shop.workshop.container
    business_id = BusinessId(shop.business_id)
    now = Microseconds(container.time_provider.microsecond_wall_clock().now_unix())
    contact = ContactDocument(business_id=business_id, created_at=now, updated_at=now)
    conversation = ConversationDocument.model_validate(
        {
            "business_id": business_id,
            "contact_id": contact.id,
            "channel": ChannelKind.WEB_CHAT,
            "channel_user_id": "visitor-their-0001",
            "assistant_version_id": str(AssistantVersionId()),
            "last_message_at": now,
            "created_at": now,
            "updated_at": now,
        }
    )
    with container.utilities.storage_scope().scoped_to_business(business_id):
        container.repositories.contact_repo().save(contact)
        container.repositories.conversation_repo().save(conversation)
    return str(conversation.id)


def make_their_records(their: IntegrationShop) -> TheirRecords:
    booking = their.book(name=THEIR_CONTACT_NAME)
    key = their.add_api_key(name="Their CRM")
    lead = their.api(
        "POST",
        "/leads",
        key,
        {"contact_name": THEIR_CONTACT_NAME, "type": "banquet", "details": "Wedding"},
    )
    assert lead.status_code == 201, lead.text
    webhook = their.api(
        "POST",
        "/webhooks",
        key,
        {
            "url": "https://hooks.zapier.com/hooks/catch/2/xyz",
            "event_types": ["lead.created"],
        },
    )
    assert webhook.status_code == 201, webhook.text
    return TheirRecords(
        business_id=their.business_id,
        booking_id=str(booking["id"]),
        contact_id=str(booking["contact_id"]),
        lead_id=str(lead.json()["id"]),
        conversation_id=store_conversation(their),
        webhook_id=str(webhook.json()["endpoint"]["id"]),
        resource_id=their.resource_id,
        key=key,
    )
