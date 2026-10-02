from dataclasses import dataclass

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.businesses import InviteStaffCommand, InviteStaffRequest
from app.schemas.dto.compliance import ContactDataCommand
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from tests.compliance.visitor_records import SeededVisitor, seed_visitor
from tests.users.accounts_phones import GEORGIA_MOBILE, GERMANY_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


@dataclass(frozen=True)
class TwoTenants:
    testbed: AccountsTestbed
    owner_id: UserId
    staff_id: UserId
    business: BusinessDocument
    visitor: SeededVisitor
    neighbour: SeededVisitor
    foreign_visitor: SeededVisitor


def seed_two_tenants() -> TwoTenants:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    staff = testbed.sign_in_with_phone(GERMANY_MOBILE)
    other_owner = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    business = testbed.create_restaurant(owner.user.id, "Sakhli")
    other_business = testbed.create_restaurant(other_owner.user.id, "Shuk")
    testbed.invite_staff.run(
        InviteStaffCommand(
            user_id=owner.user.id,
            business_id=business.id,
            invitation=InviteStaffRequest(
                phone_number=RawPhoneNumberInput(GERMANY_MOBILE)
            ),
        )
    )
    return TwoTenants(
        testbed=testbed,
        owner_id=owner.user.id,
        staff_id=staff.user.id,
        business=business,
        visitor=seed_visitor(
            testbed, business, "Giorgi", "+995577123456", "4242", "ka"
        ),
        neighbour=seed_visitor(
            testbed, business, "Nino", "+995577654321", "5353", "ru"
        ),
        foreign_visitor=seed_visitor(
            testbed, other_business, "Noa", "+972502223344", "6464", "he"
        ),
    )


def command(
    tenants: TwoTenants,
    contact_id: ContactId,
    user_id: UserId | None = None,
) -> ContactDataCommand:
    return ContactDataCommand(
        user_id=tenants.owner_id if user_id is None else user_id,
        business_id=tenants.business.id,
        contact_id=contact_id,
        client_ip_address=ClientIpAddress("192.0.2.10"),
    )


def test_export_contains_exactly_the_visitor_records() -> None:
    tenants = seed_two_tenants()
    visitor = tenants.visitor

    export = tenants.testbed.export_contact_data.run(
        command(tenants, visitor.contact.id)
    )

    records = export.records
    assert export.business_id == tenants.business.id
    assert export.exported_at == tenants.testbed.clock.now_microseconds()
    assert records.contact.id == visitor.contact.id
    assert records.contact.name == "Giorgi"
    assert {conversation.id for conversation in records.conversations} == {
        visitor.chat_conversation.id,
        visitor.phone_conversation.id,
    }
    assert {message.id for message in records.messages} == {
        message.id for message in visitor.messages
    }
    assert {call.id for call in records.calls} == {
        visitor.conversation_call.id,
        visitor.phone_matched_call.id,
    }
    assert [booking.id for booking in records.bookings] == [visitor.booking.id]
    assert [lead.id for lead in records.leads] == [visitor.lead.id]
    assert [handoff.id for handoff in records.handoffs] == [visitor.handoff.id]
    serialized_export = export.model_dump_json()
    assert "Nino" not in serialized_export
    assert "Noa" not in serialized_export

    audit_entries = tenants.testbed.audit_log_repo.list_by_business(tenants.business.id)
    export_entries = [
        entry for entry in audit_entries if entry.action is AuditAction.EXPORT
    ]
    assert len(export_entries) == 1
    assert export_entries[0].entity == "contact"
    assert export_entries[0].entity_id == str(visitor.contact.id)
    assert export_entries[0].actor_id == tenants.owner_id
    assert export_entries[0].ip_address == "192.0.2.10"


def test_data_rights_are_owner_only_and_tenant_isolated() -> None:
    tenants = seed_two_tenants()
    testbed = tenants.testbed

    with pytest.raises(AccessDeniedError):
        testbed.export_contact_data.run(
            command(tenants, tenants.visitor.contact.id, tenants.staff_id)
        )
    with pytest.raises(AccessDeniedError):
        testbed.delete_contact_data.run(
            command(tenants, tenants.visitor.contact.id, tenants.staff_id)
        )
    with pytest.raises(NotFoundError):
        testbed.export_contact_data.run(
            command(tenants, tenants.foreign_visitor.contact.id)
        )
    with pytest.raises(NotFoundError):
        testbed.delete_contact_data.run(
            command(tenants, tenants.foreign_visitor.contact.id)
        )
    with pytest.raises(NotFoundError):
        testbed.export_contact_data.run(command(tenants, ContactId()))

    foreign_contact = testbed.contact_repo.get(
        tenants.foreign_visitor.contact.business_id,
        tenants.foreign_visitor.contact.id,
    )
    assert foreign_contact is not None
    assert not any(
        entry.action in (AuditAction.EXPORT, AuditAction.DELETE)
        for entry in testbed.audit_log_repo.list_by_business(tenants.business.id)
    )


def test_erasure_deletes_personal_data_and_anonymizes_business_records() -> None:
    tenants = seed_two_tenants()
    testbed = tenants.testbed
    visitor = tenants.visitor
    testbed.clock.advance(5)

    result = testbed.delete_contact_data.run(command(tenants, visitor.contact.id))

    business_id = tenants.business.id
    erased = testbed.contact_repo.get(business_id, visitor.contact.id)
    assert erased is not None
    assert erased.erased_at == testbed.clock.now_microseconds()
    assert erased.name is None
    assert erased.phone_number is None
    assert erased.verified_phone_number is None
    assert erased.language is None
    assert erased.channel_identities == []
    assert erased.created_at == visitor.contact.created_at
    for conversation in (visitor.chat_conversation, visitor.phone_conversation):
        assert (
            testbed.message_repo.list_by_conversation(business_id, conversation.id)
            == []
        )
        assert testbed.llm_turn_repo.list_by_conversation(conversation.id) == []
        anonymized = testbed.conversation_repo.get(business_id, conversation.id)
        assert anonymized is not None
        assert anonymized.channel_user_id.startswith("erased-")
        assert anonymized.channel_user_id != conversation.channel_user_id
        assert anonymized.status is ConversationStatus.CLOSED
        assert anonymized.updated_at == testbed.clock.now_microseconds()

    for call in (visitor.conversation_call, visitor.phone_matched_call):
        erased_call = testbed.call_repo.get(business_id, call.id)
        assert erased_call is not None
        assert erased_call.recording_path is None
        assert erased_call.transcript is None
        assert erased_call.from_phone_number is None
        assert erased_call.to_phone_number == "+995322123456"
        assert erased_call.provider_call_id == call.provider_call_id
    assert set(testbed.recording_storage.deleted_paths) == {
        visitor.conversation_call.recording_path,
        visitor.phone_matched_call.recording_path,
    }
    assert len(testbed.recording_storage.deleted_paths) == 2

    booking = testbed.booking_repo.get(business_id, visitor.booking.id)
    lead = testbed.lead_repo.get(business_id, visitor.lead.id)
    handoff = testbed.handoff_repo.get(business_id, visitor.handoff.id)
    assert booking is not None and lead is not None and handoff is not None
    assert booking.notes is None
    assert booking.status is BookingStatus.CONFIRMED
    assert booking.party_size == 4
    assert "Giorgi" not in lead.details
    assert lead.budget is None
    assert lead.party_size == 40
    assert "Giorgi" not in handoff.summary

    assert result.deleted_messages == 3
    assert result.deleted_llm_turns == 3
    assert result.erased_calls == 2
    assert result.deleted_recordings == 2
    assert result.anonymized_conversations == 2
    assert result.anonymized_bookings == 1
    assert result.anonymized_leads == 1
    assert result.anonymized_handoffs == 1

    delete_entries = [
        entry
        for entry in testbed.audit_log_repo.list_by_business(business_id)
        if entry.action is AuditAction.DELETE
    ]
    assert [(entry.entity, entry.entity_id) for entry in delete_entries] == [
        ("contact", str(visitor.contact.id))
    ]
    with pytest.raises(NotFoundError):
        testbed.export_contact_data.run(command(tenants, visitor.contact.id))
    with pytest.raises(NotFoundError):
        testbed.delete_contact_data.run(command(tenants, visitor.contact.id))


def test_erasure_leaves_other_visitors_and_tenants_untouched() -> None:
    tenants = seed_two_tenants()
    testbed = tenants.testbed
    neighbour_export_before = testbed.export_contact_data.run(
        command(tenants, tenants.neighbour.contact.id)
    )

    testbed.delete_contact_data.run(command(tenants, tenants.visitor.contact.id))

    neighbour_export_after = testbed.export_contact_data.run(
        command(tenants, tenants.neighbour.contact.id)
    )
    assert neighbour_export_after.records == neighbour_export_before.records
    foreign = tenants.foreign_visitor
    foreign_business_id = foreign.contact.business_id
    assert testbed.contact_repo.get(foreign_business_id, foreign.contact.id) is not None
    assert (
        len(
            testbed.message_repo.list_by_conversation(
                foreign_business_id,
                foreign.chat_conversation.id,
            )
        )
        == 2
    )
    assert (
        len(testbed.llm_turn_repo.list_by_conversation(foreign.chat_conversation.id))
        == 2
    )
    foreign_call = testbed.call_repo.get(
        foreign_business_id, foreign.conversation_call.id
    )
    assert foreign_call is not None
    assert foreign_call.transcript is not None


def test_storage_failure_leaves_the_database_untouched_for_a_retry() -> None:
    tenants = seed_two_tenants()
    testbed = tenants.testbed
    testbed.recording_storage.is_failing = True

    with pytest.raises(ExternalServiceError):
        testbed.delete_contact_data.run(command(tenants, tenants.visitor.contact.id))

    business_id = tenants.business.id
    assert testbed.contact_repo.get(business_id, tenants.visitor.contact.id) is not None
    call = testbed.call_repo.get(business_id, tenants.visitor.conversation_call.id)
    assert call is not None
    assert call.recording_path is not None

    testbed.recording_storage.is_failing = False
    result = testbed.delete_contact_data.run(
        command(tenants, tenants.visitor.contact.id)
    )
    assert result.deleted_recordings == 2


def test_visitor_without_phone_or_records_is_erased_cleanly() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    contact = ContactDocument(business_id=business.id)
    testbed.contact_repo.save(contact)

    result = testbed.delete_contact_data.run(
        ContactDataCommand(
            user_id=owner.user.id,
            business_id=business.id,
            contact_id=contact.id,
        )
    )

    assert result.deleted_messages == 0
    assert result.erased_calls == 0
    erased = testbed.contact_repo.get(business.id, contact.id)
    assert erased is not None
    assert erased.erased_at is not None
