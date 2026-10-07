"""
What a scenario's customer already has with the business before the
conversation (dataset_setup_models): the persona as a WhatsApp contact whose
phone the channel proved, a booking still to come (booked with the product's
own create-booking use case, so it is placed and priced like a real one),
an earlier conversation the customer memory recalls with the team's note on
it and an order the team has not closed, and another customer an attacker
asks about. Every row carries the run's clock, so the conversation the model
sees is the same in every run (and its recorded answers replay).
"""

from typed_time_provider import Microseconds

from app.containers.app import AppContainer
from app.schemas.constants.bookings import LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.domain.assistant_settings import AssistantSettingsDocument
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.bookings import CreateBookingCommand
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    NightCount,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSummaryText,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.inbox.constrained_strings import ConversationNoteText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId
from scripts.eval_harness.business_seeding import SeededBusiness
from scripts.eval_harness.dataset_models import ScenarioSpec
from scripts.eval_harness.dataset_setup_models import (
    BookingSeedSpec,
    EarlierConversationSpec,
    ScenarioChannel,
)

CUSTOMER_CHANNEL: ChannelKind = ChannelKind.WHATSAPP
MICROSECONDS_PER_HOUR: int = 3_600_000_000
HOURS_PER_DAY: int = 24


def customer_channel_user_id(phone: str) -> ChannelUserId:
    """A WhatsApp user id: the international number without the plus."""

    return ChannelUserId(
        "".join(character for character in phone if character.isdigit())
    )


def seed_customer(
    container: AppContainer,
    seeded: SeededBusiness,
    scenario: ScenarioSpec,
    owner_id: UserId,
) -> None:
    """The scenario's customer and what they have; nothing for an owner test."""

    if scenario.channel is ScenarioChannel.OWNER_TEST or not scenario.persona.phone:
        return

    business_id = seeded.business.id
    now: Microseconds = container.time_provider.microsecond_wall_clock().now_unix()
    language = LanguageTag(scenario.language)
    with container.utilities.storage_scope().scoped_to_business(business_id):
        contact: ContactDocument = save_contact(
            container, seeded, scenario.persona.name, scenario.persona.phone, now
        )
        setup = scenario.setup
        if setup is None:
            return

        if setup.booking is not None:
            book(container, seeded, contact, setup.booking, language)

        if setup.earlier is not None:
            remember(container, seeded, contact, setup.earlier, owner_id, now)

        other = setup.other_customer
        if other is not None:
            other_contact = save_contact(
                container, seeded, other.name, other.phone, now
            )
            if other.booking is not None:
                book(container, seeded, other_contact, other.booking, language)


def save_contact(
    container: AppContainer,
    seeded: SeededBusiness,
    name: str,
    phone: str,
    now: Microseconds,
) -> ContactDocument:
    """A customer who wrote from WhatsApp before: their number is proven."""

    number = E164PhoneNumber(phone)
    contact = ContactDocument(
        business_id=seeded.business.id,
        name=ContactName(name),
        phone_number=number,
        verified_phone_number=number,
        channel_identities=[
            ChannelIdentity(
                channel=CUSTOMER_CHANNEL,
                channel_user_id=customer_channel_user_id(phone),
            )
        ],
        created_at=now,
        updated_at=now,
    )
    container.repositories.contact_repo().save(contact)
    return contact


def book(
    container: AppContainer,
    seeded: SeededBusiness,
    contact: ContactDocument,
    booking: BookingSeedSpec,
    language: LanguageTag,
) -> None:
    """A real (not sandbox) booking of the contact, as create_booking makes it."""

    container.use_cases.bookings.create_booking_use_case().run(
        CreateBookingCommand(
            business_id=seeded.business.id,
            contact_id=contact.id,
            contact_name=contact.name or ContactName("Guest"),
            contact_phone_number=contact.verified_phone_number,
            date=LocalDate(booking.date),
            time=None if booking.time is None else LocalTimeOfDay(booking.time),
            duration_minutes=(
                None
                if booking.duration_minutes is None
                else BookingDurationMinutes(booking.duration_minutes)
            ),
            nights=None if booking.nights is None else NightCount(booking.nights),
            party_size=PartySize(booking.party_size),
            source_channel=CUSTOMER_CHANNEL,
            language=language,
        )
    )


def remember(
    container: AppContainer,
    seeded: SeededBusiness,
    contact: ContactDocument,
    earlier: EarlierConversationSpec,
    owner_id: UserId,
    now: Microseconds,
) -> None:
    """An earlier, summarized conversation; its note and open order; notes shared."""

    business_id = seeded.business.id
    at = Microseconds(
        int(now) - earlier.days_ago * HOURS_PER_DAY * MICROSECONDS_PER_HOUR
    )
    later = Microseconds(int(at) + MICROSECONDS_PER_HOUR)
    repositories = container.repositories
    conversation = ConversationDocument(
        business_id=business_id,
        contact_id=contact.id,
        assistant_version_id=seeded.version.id,
        channel=CUSTOMER_CHANNEL,
        channel_user_id=contact.channel_identities[0].channel_user_id,
        status=ConversationStatus.CLOSED,
        last_message_at=at,
        summary=ConversationSummaryText(earlier.summary),
        summarized_at=later,
        created_at=at,
        updated_at=later,
    )
    repositories.conversation_repo().save(conversation)
    if earlier.lead is not None:
        repositories.lead_repo().save(
            LeadDocument(
                business_id=business_id,
                contact_id=contact.id,
                conversation_id=conversation.id,
                lead_type=LeadType.ORDER,
                details=LeadDetails(earlier.lead),
                source_channel=CUSTOMER_CHANNEL,
                created_at=at,
                updated_at=at,
            )
        )

    if earlier.note is None:
        return

    repositories.conversation_note_repo().add(
        ConversationNoteDocument(
            business_id=business_id,
            conversation_id=conversation.id,
            author_user_id=owner_id,
            text=ConversationNoteText(earlier.note),
            created_at=later,
            updated_at=later,
        )
    )
    # The owner shares the team's notes with the assistant (Settings ->
    # General): the note reaches the model, which must never quote it.
    repositories.assistant_settings_repo().change(business_id, share_notes, now)


def share_notes(settings: AssistantSettingsDocument) -> None:
    settings.shares_team_notes = True
