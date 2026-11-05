"""What the customer memory remembered of a visitor is erased with them."""

from typed_time_provider import Microseconds

from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.customer_memory.conversation_summaries import (
    ConversationSummaryWrite,
)
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSummaryText,
)
from tests.compliance.two_tenants import TwoTenants, command, seed_two_tenants


def summarize(
    tenants: TwoTenants, conversation: ConversationDocument, text: str
) -> ConversationDocument | None:
    stored = tenants.testbed.conversation_repo.get(
        conversation.business_id, conversation.id
    )
    assert stored is not None
    return tenants.testbed.conversation_repo.set_summary(
        conversation.business_id,
        conversation.id,
        ConversationSummaryWrite(
            summary=ConversationSummaryText(text),
            written_at=Microseconds(int(stored.last_message_at) + 1),
            covers_until=stored.last_message_at,
        ),
    )


def stored_summary(
    tenants: TwoTenants, conversation: ConversationDocument
) -> str | None:
    stored = tenants.testbed.conversation_repo.get(
        conversation.business_id, conversation.id
    )
    assert stored is not None
    return None if stored.summary is None else str(stored.summary)


def test_erasure_clears_the_visitor_summaries_and_keeps_everyone_else() -> None:
    tenants = seed_two_tenants()
    visitor, neighbour = tenants.visitor, tenants.neighbour
    for conversation in (visitor.chat_conversation, visitor.phone_conversation):
        assert summarize(tenants, conversation, "Booked a table by the window.")
    assert summarize(tenants, neighbour.chat_conversation, "Asked about wine.")

    tenants.testbed.delete_contact_data.run(command(tenants, visitor.contact.id))

    for conversation in (visitor.chat_conversation, visitor.phone_conversation):
        assert stored_summary(tenants, conversation) is None
    assert stored_summary(tenants, neighbour.chat_conversation) == "Asked about wine."


def test_a_summary_written_after_the_erasure_is_refused() -> None:
    tenants = seed_two_tenants()
    conversation = tenants.visitor.chat_conversation
    tenants.testbed.delete_contact_data.run(
        command(tenants, tenants.visitor.contact.id)
    )

    assert summarize(tenants, conversation, "Booked a table.") is None
    assert stored_summary(tenants, conversation) is None
