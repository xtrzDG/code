"""
What an erasure and the retention purge leave of business records, and
that a record anonymized already is not written again.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffSummaryCode
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.conversations import CallDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.bookings.strings import (
    BookingNote,
    LeadBudgetText,
    LeadDetails,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.use_cases.compliance.record_anonymization import (
    ERASED_TEXT,
    EXPIRED_TEXT,
    anonymized_booking,
    anonymized_handoff,
    anonymized_lead,
    erased_call,
)

NOW: Microseconds = Microseconds(1_790_000_000_000_000)
BUSINESS: BusinessId = BusinessId()
CUSTOMER_PHONE: E164PhoneNumber = E164PhoneNumber("+995555123456")
BUSINESS_PHONE: E164PhoneNumber = E164PhoneNumber("+995322123456")


def test_a_lead_keeps_its_kind_and_loses_details_and_budget_once() -> None:
    lead = LeadDocument(
        business_id=BUSINESS,
        contact_id=ContactId(),
        lead_type=LeadType.BANQUET,
        details=LeadDetails("Nino's wedding"),
        budget=LeadBudgetText("3000 GEL"),
        source_channel=ChannelKind.TELEGRAM,
    )

    anonymized = anonymized_lead(lead, EXPIRED_TEXT, NOW)

    assert anonymized is not None
    assert (anonymized.details, anonymized.budget) == (EXPIRED_TEXT, None)
    assert anonymized.lead_type is LeadType.BANQUET
    assert anonymized_lead(anonymized, ERASED_TEXT, NOW) is None


def test_a_booking_loses_its_notes_once() -> None:
    booking = BookingDocument(
        business_id=BUSINESS,
        resource_id=ResourceId(),
        contact_id=ContactId(),
        starts_at=BookingStartsAtUnixSeconds(1_790_000_000),
        ends_at=BookingEndsAtUnixSeconds(1_790_003_600),
        party_size=PartySize(2),
        status=BookingStatus.COMPLETED,
        source_channel=ChannelKind.WHATSAPP,
        notes=BookingNote("Window seat for Nino"),
    )

    anonymized = anonymized_booking(booking, NOW)

    assert anonymized is not None and anonymized.notes is None
    assert anonymized_booking(anonymized, NOW) is None


def test_a_handoff_loses_summary_quotes_and_flags_once() -> None:
    handoff = HandoffDocument(
        business_id=BUSINESS,
        conversation_id=ConversationId(),
        contact_id=ContactId(),
        reason=HandoffReason.COMPLAINT,
        summary=HandoffSummary("Nino complains"),
    )

    anonymized = anonymized_handoff(
        handoff, ERASED_TEXT, HandoffSummaryCode.DATA_ERASED, NOW
    )

    assert anonymized is not None
    assert anonymized.summary_code is HandoffSummaryCode.DATA_ERASED
    assert anonymized_handoff(anonymized, EXPIRED_TEXT, None, NOW) is None


def test_a_call_keeps_the_business_number_unless_no_customer_is_named() -> None:
    call = CallDocument(
        business_id=BUSINESS,
        from_phone_number=CUSTOMER_PHONE,
        to_phone_number=BUSINESS_PHONE,
        started_at=NOW,
        provider_call_id=ProviderCallId("conv_1"),
    )

    erased = erased_call(call.model_copy(), NOW, CUSTOMER_PHONE)
    purged = erased_call(call.model_copy(), NOW)

    assert erased is not None and erased.to_phone_number == BUSINESS_PHONE
    assert erased.from_phone_number is None
    assert purged is not None and purged.to_phone_number is None
    assert erased_call(purged, NOW) is None
