"""
The customer's marketing consent on the team's card: recorded in person by
the team, taken back, never shown as "agreed" while messages are stopped,
and kept by every plain save of the contact.
"""

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.marketing_consent import (
    CURRENT_MARKETING_CONSENT_TEXT,
    MarketingConsentSource,
    MarketingConsentStatus,
    MarketingConsentWithdrawal,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.customers.customer_card import (
    ChangeCustomerCardCommand,
    CustomerCardRequest,
    CustomerCardView,
)
from app.schemas.typings.contacts.booleans import IsMarketingConsentGiven
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.privacy.suppressed_identities import contact_identities
from tests.customers.customer_bed import CLIENT_IP, CustomerBed


def record(
    bed: CustomerBed, contact_id: ContactId, is_given: bool, user_id: UserId
) -> CustomerCardView:
    return bed.change_card.run(
        ChangeCustomerCardCommand(
            user_id=user_id,
            business_id=bed.customers.business.id,
            contact_id=contact_id,
            request=CustomerCardRequest(
                marketing_consent=IsMarketingConsentGiven(is_given)
            ),
            client_ip_address=CLIENT_IP,
        )
    )


def stored(bed: CustomerBed, contact_id: ContactId) -> ContactDocument:
    contact = bed.customers.testbed.contact_repo.get(
        bed.customers.business.id, contact_id
    )
    assert contact is not None
    return contact


def test_every_customer_starts_without_consent() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi.contact

    detail = bed.customers.testbed.get_contact.run(bed.contact_query(giorgi.id))

    assert detail.marketing_consent.status is MarketingConsentStatus.NOT_GIVEN
    assert detail.marketing_consent.given_at is None


def test_staff_record_a_consent_given_in_person_with_its_wording() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi.contact

    card = record(bed, giorgi.id, True, bed.staff_id)

    consent = card.marketing_consent
    assert consent.status is MarketingConsentStatus.AGREED
    assert consent.source is MarketingConsentSource.IN_PERSON
    assert consent.recorded_by == bed.staff_id
    assert consent.text_version is CURRENT_MARKETING_CONSENT_TEXT
    assert consent.given_at == bed.customers.testbed.clock.now_microseconds()
    entry = bed.customers.testbed.audit_log_repo.list_by_business(
        bed.customers.business.id
    )[-1]
    assert (entry.action, entry.entity, entry.entity_id, entry.actor_id) == (
        AuditAction.UPDATE,
        "contact",
        str(giorgi.id),
        bed.staff_id,
    )


def test_agreeing_again_keeps_the_first_consent() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi.contact
    first = record(bed, giorgi.id, True, bed.staff_id)
    bed.customers.testbed.clock.advance(seconds=60)

    again = record(bed, giorgi.id, True, bed.owner_id)

    assert again.marketing_consent == first.marketing_consent


def test_a_consent_taken_back_in_person_says_who_and_how() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi.contact
    record(bed, giorgi.id, True, bed.staff_id)

    card = record(bed, giorgi.id, False, bed.owner_id)

    assert card.marketing_consent.status is MarketingConsentStatus.WITHDRAWN
    assert card.marketing_consent.withdrawal is MarketingConsentWithdrawal.IN_PERSON
    consent = stored(bed, giorgi.id).marketing_consent
    assert consent is not None and consent.withdrawn_by == bed.owner_id
    # Taking back what is taken back changes nothing; agreeing again is new.
    assert record(bed, giorgi.id, False, bed.staff_id) == card
    renewed = record(bed, giorgi.id, True, bed.staff_id).marketing_consent
    assert renewed.status is MarketingConsentStatus.AGREED
    assert renewed.withdrawn_at is None


def test_a_suppressed_or_blocked_customer_never_reads_as_agreed() -> None:
    bed = CustomerBed()
    testbed = bed.customers.testbed
    giorgi = bed.customers.giorgi.contact
    nino = bed.customers.nino.contact
    record(bed, giorgi.id, True, bed.staff_id)
    record(bed, nino.id, True, bed.staff_id)
    testbed.suppression_list.suppress(
        bed.customers.business.id,
        contact_identities(stored(bed, giorgi.id)),
        testbed.clock.now_microseconds(),
    )

    detail = testbed.get_contact.run(bed.contact_query(giorgi.id))
    blocked = bed.block(nino.id)

    assert detail.marketing_consent.status is MarketingConsentStatus.STOPPED
    assert detail.marketing_consent.source is MarketingConsentSource.IN_PERSON
    assert blocked.marketing_consent.status is MarketingConsentStatus.STOPPED
    assert (
        bed.block(nino.id, is_blocked=False).marketing_consent.status
        is MarketingConsentStatus.AGREED
    )


def test_a_plain_save_keeps_the_consent_and_a_new_stop_takes_it_back() -> None:
    bed = CustomerBed()
    testbed = bed.customers.testbed
    giorgi = bed.customers.giorgi.contact
    read_before = stored(bed, giorgi.id)
    record(bed, giorgi.id, True, bed.staff_id)

    # A turn that read the contact before the consent saves it afterwards.
    read_before.language = None
    testbed.contact_repo.save(read_before)
    assert stored(bed, giorgi.id).has_marketing_consent

    stopped = stored(bed, giorgi.id)
    testbed.clock.advance(seconds=30)
    stopped.opted_out_channels = [ChannelKind.TELEGRAM]
    stopped.updated_at = testbed.clock.now_microseconds()
    testbed.contact_repo.save(stopped)

    consent = stored(bed, giorgi.id).marketing_consent
    assert consent is not None
    assert consent.withdrawal is MarketingConsentWithdrawal.STOP
    assert consent.withdrawn_at == testbed.clock.now_microseconds()
    assert consent.withdrawn_by is None
