"""Waiting items of a business for the attention count tests."""

from app.schemas.constants.bookings import BookingStatus, LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import HandoffReason, HandoffStatus, HandoffUrgency
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.handoffs.strings import HandoffSummary
from tests.operations.operations_world import OperationsWorld

UPCOMING: tuple[str, str] = ("2026-10-06T19:00:00+04:00", "2026-10-06T21:00:00+04:00")
# The clock of the operations world stands at 12:00 in Tbilisi on Oct 5.
STARTED: tuple[str, str] = ("2026-10-05T11:30:00+04:00", "2026-10-05T13:00:00+04:00")


def add_handoff(
    world: OperationsWorld,
    business: BusinessDocument,
    contact: ContactDocument,
    status: HandoffStatus,
    is_sandbox: bool = False,
) -> None:
    conversation = world.add_conversation(business, contact, is_sandbox=is_sandbox)
    if status is not HandoffStatus.RESOLVED:
        conversation.status = ConversationStatus.HANDOFF
        world.conversation_repo.save(conversation)
    world.handoff_repo.save(
        HandoffDocument(
            business_id=business.id,
            conversation_id=conversation.id,
            contact_id=contact.id,
            reason=HandoffReason.CUSTOMER_REQUEST,
            summary=HandoffSummary("Wants to talk to the manager"),
            urgency=HandoffUrgency.NORMAL,
            status=status,
            is_sandbox=is_sandbox,
        )
    )


def add_lead(
    world: OperationsWorld,
    business: BusinessDocument,
    contact: ContactDocument,
    status: LeadStatus,
    is_sandbox: bool = False,
) -> None:
    conversation = world.add_conversation(business, contact, is_sandbox=is_sandbox)
    if status in (LeadStatus.NEW, LeadStatus.IN_PROGRESS):
        world.conversation_repo.set_open_request(
            business.id, conversation.id, True, world.clock.now_microseconds()
        )
    world.lead_repo.save(
        LeadDocument(
            business_id=business.id,
            contact_id=contact.id,
            conversation_id=conversation.id,
            lead_type=LeadType.BANQUET,
            details=LeadDetails("A birthday for 30 guests"),
            source_channel=ChannelKind.WHATSAPP,
            status=status,
            is_sandbox=is_sandbox,
        )
    )


def add_channel(
    world: OperationsWorld,
    business: BusinessDocument,
    kind: ChannelKind,
    status: ChannelStatus,
) -> None:
    channel = ChannelDocument(business_id=business.id, kind=kind, status=status)
    world.channel_collection.upsert(str(channel.id), channel)


def seed_waiting_items(
    world: OperationsWorld,
    business: BusinessDocument,
    other_business: BusinessDocument,
) -> None:
    """
    3 conversations that need a person, 2 with an open request (none
    assigned), 1 booking to confirm, 1 failing channel; the sandbox and the
    other business add nothing.
    """

    resource = world.add_resource(business, "Table 4")
    contact = world.add_contact(business, "Nino", "+995555123456")
    for status in HandoffStatus:
        add_handoff(world, business, contact, status)
    add_handoff(world, business, contact, HandoffStatus.PENDING, is_sandbox=True)
    for lead_status in (LeadStatus.NEW, LeadStatus.NEW, LeadStatus.WON):
        add_lead(world, business, contact, lead_status)
    add_lead(world, business, contact, LeadStatus.NEW, is_sandbox=True)
    world.add_booking(business, resource, contact, *UPCOMING, BookingStatus.PENDING)
    world.add_booking(business, resource, contact, *STARTED, BookingStatus.PENDING)
    world.add_booking(business, resource, contact, *UPCOMING, BookingStatus.CONFIRMED)
    world.add_booking(
        business, resource, contact, *UPCOMING, BookingStatus.PENDING, is_sandbox=True
    )
    add_channel(world, business, ChannelKind.TELEGRAM, ChannelStatus.ERROR)
    add_channel(world, business, ChannelKind.WHATSAPP, ChannelStatus.CONNECTED)
    add_channel(world, other_business, ChannelKind.TELEGRAM, ChannelStatus.ERROR)
