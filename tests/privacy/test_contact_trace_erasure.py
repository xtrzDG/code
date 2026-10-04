"""
Erasure and export reach a visitor's traces outside their conversations:
missed calls (by their number), the outbox (their account), the inbox
(their account and conversations) and requests for feedback (the contact),
and leave other visitors' traces alone.
"""

from app.schemas.constants.deliveries import InboundEventStatus, OutboundMessageStatus
from app.schemas.typings.compliance.constrained_integers import ErasedRecordCount
from tests.compliance.two_tenants import command, seed_two_tenants
from tests.privacy.contact_trace_seeds import seed_traces


def test_export_lists_missed_calls_queued_messages_events_and_ratings() -> None:
    tenants = seed_two_tenants()
    testbed = tenants.testbed
    mine = seed_traces(testbed, tenants.visitor, "Giorgi")
    seed_traces(testbed, tenants.neighbour, "Nino")

    export = testbed.export_contact_data.run(
        command(tenants, tenants.visitor.contact.id)
    )

    records = export.records
    assert [call.id for call in records.missed_calls] == [mine.missed_call.id]
    assert [message.id for message in records.outbound_messages] == [mine.reminder.id]
    assert [event.id for event in records.inbound_events] == [mine.inbound_event.id]
    assert [request.score for request in records.feedback_requests] == [5]
    assert export.opt_out.opted_out_channels == []
    assert export.opt_out.is_on_suppression_list is False
    assert "Nino" not in export.model_dump_json()


def test_erasure_removes_the_number_texts_and_accounts_of_every_trace() -> None:
    tenants = seed_two_tenants()
    testbed = tenants.testbed
    mine = seed_traces(testbed, tenants.visitor, "Giorgi")
    neighbour = seed_traces(testbed, tenants.neighbour, "Nino")
    business_id = tenants.business.id

    result = testbed.delete_contact_data.run(
        command(tenants, tenants.visitor.contact.id)
    )

    assert result.erased_missed_calls == ErasedRecordCount(1)
    assert result.redacted_outbound_messages == ErasedRecordCount(1)
    assert result.redacted_inbound_events == ErasedRecordCount(1)
    assert result.anonymized_feedback_requests == ErasedRecordCount(1)

    missed = testbed.missed_call_repo.get(business_id, mine.missed_call.id)
    assert missed is not None and missed.caller_phone_number is None
    reminder = testbed.outbound_message_repo.get(business_id, mine.reminder.id)
    assert reminder is not None
    assert reminder.status is OutboundMessageStatus.DEAD
    assert "Giorgi" not in reminder.model_dump_json()
    assert str(tenants.visitor.chat_conversation.channel_user_id) not in str(
        reminder.recipient_key
    )
    event = testbed.inbound_event_repo.get(business_id, mine.inbound_event.id)
    assert event is not None
    assert event.status is InboundEventStatus.FAILED
    assert "Giorgi" not in event.model_dump_json()
    assert "+995577123456" not in event.model_dump_json()
    request = testbed.feedback_request_repo.get(business_id, mine.feedback_request.id)
    assert request is not None
    assert request.review_token is None
    assert request.score == 5

    # The neighbour's traces are untouched.
    other_call = testbed.missed_call_repo.get(business_id, neighbour.missed_call.id)
    assert other_call is not None and other_call.caller_phone_number is not None
    other_reminder = testbed.outbound_message_repo.get(
        business_id, neighbour.reminder.id
    )
    assert other_reminder is not None
    assert other_reminder.status is OutboundMessageStatus.PENDING
    other_event = testbed.inbound_event_repo.get(
        business_id, neighbour.inbound_event.id
    )
    assert other_event is not None and "Nino" in other_event.model_dump_json()


def test_erasure_finds_the_missed_call_by_the_number_after_the_contact() -> None:
    tenants = seed_two_tenants()
    testbed = tenants.testbed
    mine = seed_traces(testbed, tenants.visitor, "Giorgi")

    testbed.delete_contact_data.run(command(tenants, tenants.visitor.contact.id))

    assert (
        testbed.missed_call_repo.list_by_caller(
            tenants.business.id,
            mine.missed_call.caller_phone_number,  # type: ignore[arg-type]
        )
        == []
    )
