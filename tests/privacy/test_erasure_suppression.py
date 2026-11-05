"""
Every erased customer leaves a suppression hash (PRIV-08): digests of their
numbers and accounts as erasure entries, apart from STOP. They never hold
back a message the customer asks for (a new booking's reminder), never
lift with START, and keep any marketing on a consent given before the
erasure (another contact with the same number) from reaching them. The
erasure also hands the customer's bookings, as it left them, to the
business's calendar, which forgets the guest.
"""

from datetime import datetime

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.privacy_repositories import SuppressionEntryRepository
from app.schemas.constants.campaigns import CampaignMessageStatus, CampaignSkipReason
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.suppression import SuppressionEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.privacy.messaging_suppression import is_messaging_suppressed
from app.utilities.privacy.suppressed_identities import (
    contact_identities,
    phone_identity,
)
from tests.campaigns.campaign_world import CampaignWorld
from tests.compliance.two_tenants import command, seed_two_tenants
from tests.privacy.suppression_doubles import build_suppression_list

BUSINESS: BusinessId = BusinessId()
OTHER_BUSINESS: BusinessId = BusinessId()
NUMBER: E164PhoneNumber = E164PhoneNumber("+393471234567")
VISIT_STARTS: str = "2026-09-04T19:00:00+04:00"
VISIT_ENDS: str = "2026-09-04T21:00:00+04:00"


def test_an_erasure_entry_dates_the_erasure_and_suppresses_nothing() -> None:
    stored = InMemoryDocumentCollectionAdapter(SuppressionEntryDocument)
    suppression_list = build_suppression_list(SuppressionEntryRepository(stored))
    identity = phone_identity(NUMBER)

    first = suppression_list.remember_erasure(BUSINESS, [identity], Microseconds(10))
    again = suppression_list.remember_erasure(BUSINESS, [identity], Microseconds(20))

    assert (int(first), int(again)) == (1, 0)
    assert suppression_list.erased_at(BUSINESS, [identity]) == Microseconds(20)
    assert suppression_list.erased_at(OTHER_BUSINESS, [identity]) is None
    assert suppression_list.erased_at(BUSINESS, []) is None
    assert suppression_list.is_suppressed(BUSINESS, [identity]) is False
    assert int(suppression_list.lift(BUSINESS, [identity])) == 0
    assert suppression_list.erased_at(BUSINESS, [identity]) == Microseconds(20)
    [entry] = stored.list_all()
    assert "3471234567" not in entry.model_dump_json()


def test_a_stop_and_an_erasure_of_the_same_number_keep_both_meanings() -> None:
    suppression_list = build_suppression_list()
    identity = phone_identity(NUMBER)

    suppression_list.suppress(BUSINESS, [identity], Microseconds(5))
    suppression_list.remember_erasure(BUSINESS, [identity], Microseconds(10))

    assert suppression_list.is_suppressed(BUSINESS, [identity]) is True
    assert suppression_list.erased_at(BUSINESS, [identity]) == Microseconds(10)
    suppression_list.lift(BUSINESS, [identity])
    assert suppression_list.is_suppressed(BUSINESS, [identity]) is False
    assert suppression_list.erased_at(BUSINESS, [identity]) == Microseconds(10)


def test_every_erased_customer_leaves_a_hash_but_can_still_book_again() -> None:
    tenants = seed_two_tenants()
    visitor = tenants.visitor.contact
    identities = contact_identities(visitor)
    assert not visitor.opted_out_channels

    tenants.testbed.delete_contact_data.run(command(tenants, visitor.id))

    testbed = tenants.testbed
    erased_at = testbed.suppression_list.erased_at(tenants.business.id, identities)
    assert erased_at == testbed.clock.now_microseconds()
    returning = ContactDocument(
        business_id=tenants.business.id,
        phone_number=visitor.phone_number,
        created_at=testbed.clock.now_microseconds(),
        updated_at=testbed.clock.now_microseconds(),
    )
    # A new booking's reminder still reaches the returning customer.
    assert not is_messaging_suppressed(
        testbed.suppression_list, tenants.business.id, returning
    )


def test_the_erasure_hands_the_bookings_without_notes_to_the_calendar() -> None:
    tenants = seed_two_tenants()
    booking = tenants.visitor.booking

    tenants.testbed.delete_contact_data.run(
        command(tenants, tenants.visitor.contact.id)
    )

    [forgotten] = tenants.testbed.calendar_erasure.forgotten
    assert forgotten.id == booking.id
    assert forgotten.notes is None


def test_marketing_on_a_consent_from_before_an_erasure_never_goes() -> None:
    world = CampaignWorld()
    world.enable()
    restored = world.guest("Giulia", "en")
    world.visit(restored, VISIT_STARTS, VISIT_ENDS)
    consented_after = world.guest("Marco", "en")
    world.visit(consented_after, VISIT_STARTS, VISIT_ENDS)
    # Both were erased once; Marco agreed again after he came back.
    for guest in (restored, consented_after):
        world.suppression_list.remember_erasure(
            world.business.id,
            contact_identities(guest),
            world.clock.now_microseconds(),
        )
    world.clock.move_to(datetime.fromisoformat("2026-10-05T08:05:00+00:00"))
    world.agree(consented_after)

    assert int(world.run_campaigns().processed_count) == 1
    [skipped] = world.messages_of(restored)
    assert skipped.status is CampaignMessageStatus.SKIPPED
    assert skipped.skip_reason is CampaignSkipReason.OPTED_OUT
    [sent] = world.messages_of(consented_after)
    assert sent.status is CampaignMessageStatus.SENT
    assert sent.channel is ChannelKind.TELEGRAM
