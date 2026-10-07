"""
What the event publisher's observer turns into webhook deliveries: the
observer-only announcements (a conversation started, a call finished),
nothing for test chats, one delivery per once-only event however often it
is announced, and no failure for a record that is gone.
"""

from base_typed_id import BasePrefixedTypedId
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ProviderCallId
from tests.integrations.integration_shop import IntegrationShop, open_integration_shop


def publish(
    shop: IntegrationShop,
    kind: LiveEventKind,
    record_id: BasePrefixedTypedId,
    is_sandbox: bool = False,
) -> None:
    publisher = shop.workshop.container.facilitators.event_publisher()
    scope = shop.workshop.container.utilities.storage_scope()
    with scope.scoped_to_business(BusinessId(shop.business_id)):
        publisher.publish(
            BusinessId(shop.business_id), kind, (record_id,), is_sandbox=is_sandbox
        )


def store_conversation(shop: IntegrationShop, is_sandbox: bool = False) -> str:
    container = shop.workshop.container
    business_id = BusinessId(shop.business_id)
    now = Microseconds(container.time_provider.microsecond_wall_clock().now_unix())
    contact = ContactDocument(business_id=business_id, created_at=now, updated_at=now)
    conversation = ConversationDocument.model_validate(
        {
            "business_id": business_id,
            "contact_id": contact.id,
            "channel": ChannelKind.WEB_CHAT,
            "channel_user_id": "visitor-0001",
            "assistant_version_id": str(AssistantVersionId()),
            "is_sandbox": is_sandbox,
            "last_message_at": now,
            "created_at": now,
            "updated_at": now,
        }
    )
    with container.utilities.storage_scope().scoped_to_business(business_id):
        container.repositories.contact_repo().save(contact)
        container.repositories.conversation_repo().save(conversation)
    return str(conversation.id)


def test_a_started_conversation_and_a_finished_call_are_posted() -> None:
    with open_integration_shop() as shop:
        shop.add_webhook(["conversation.started", "call.finished"])
        conversation_id = store_conversation(shop)
        container = shop.workshop.container
        now = Microseconds(container.time_provider.microsecond_wall_clock().now_unix())
        call = CallDocument(
            business_id=BusinessId(shop.business_id),
            conversation_id=ConversationId(conversation_id),
            started_at=now,
            provider_call_id=ProviderCallId("conv_test_0001"),
            created_at=now,
            updated_at=now,
        )
        scope = container.utilities.storage_scope()
        with scope.scoped_to_business(BusinessId(shop.business_id)):
            container.repositories.call_repo().save(call)
        publish(
            shop, LiveEventKind.CONVERSATION_STARTED, ConversationId(conversation_id)
        )
        publish(
            shop, LiveEventKind.CONVERSATION_STARTED, ConversationId(conversation_id)
        )
        publish(shop, LiveEventKind.CALL_FINISHED, call.id)
        shop.run_jobs()
        posted = [str(request.event_type) for request in shop.receivers.posted]

    assert posted == ["conversation.started", "call.finished"]


def test_test_chats_and_missing_records_are_not_posted() -> None:
    with open_integration_shop() as shop:
        shop.add_webhook(["conversation.started"])
        sandbox_id = store_conversation(shop, is_sandbox=True)
        publish(
            shop,
            LiveEventKind.CONVERSATION_STARTED,
            ConversationId(sandbox_id),
            is_sandbox=True,
        )
        publish(shop, LiveEventKind.CONVERSATION_STARTED, ConversationId())
        shop.run_jobs()

    assert shop.receivers.posted == []
