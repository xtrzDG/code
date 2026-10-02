"""Who a manual booking is for: the conversation, the contact, the language."""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.operations.bookings import ManualBookingCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.use_cases.bookings.operations_support import (
    CONTACT_ENTITY,
    ContactDetails,
    build_audit_entry,
    require_contact,
    update_contact_details,
)


def customer_language(
    command: ManualBookingCommand,
    contact: ContactDocument,
    conversation: ConversationDocument | None,
    business: BusinessDocument,
) -> LanguageTag:
    """Given, else the contact's, else the conversation's, else the default."""

    if command.language is not None:
        return command.language

    if contact.language is not None:
        return contact.language

    if conversation is not None and conversation.language is not None:
        return conversation.language

    return business.default_language


def find_booking_conversation(
    conversation_repo: ConversationRepoContract,
    command: ManualBookingCommand,
) -> ConversationDocument | None:
    """The conversation the booking is made from, if any."""

    if command.conversation_id is None:
        return None

    conversation: ConversationDocument | None = conversation_repo.get(
        command.business_id, command.conversation_id
    )
    if conversation is None:
        raise NotFoundError(f"Conversation {command.conversation_id} was not found.")

    return conversation


def find_existing_contact(
    contact_repo: ContactRepoContract,
    command: ManualBookingCommand,
    conversation: ConversationDocument | None,
    phone_number: E164PhoneNumber | None,
) -> ContactDocument | None:
    """The conversation's customer, else a contact with the phone, if any."""

    if conversation is not None:
        return require_contact(
            contact_repo, command.business_id, conversation.contact_id
        )

    if phone_number is not None:
        return contact_repo.find_by_phone_number(command.business_id, phone_number)

    return None


def store_booking_contact(
    contact_repo: ContactRepoContract,
    audit_log_repo: AuditLogRepoContract,
    contact: ContactDocument,
    existing_contact: ContactDocument | None,
    command: ManualBookingCommand,
    phone_number: E164PhoneNumber | None,
    now: Microseconds,
) -> ContactDocument:
    """
    Save a new contact, or update the name of a reused one (and its phone
    when booking for a conversation's customer).
    """

    if existing_contact is not None:
        return update_contact_details(
            contact_repo,
            audit_log_repo,
            existing_contact,
            ContactDetails(
                command.contact_name,
                None if command.conversation_id is None else phone_number,
            ),
            command.actor_id,
            now,
        )

    contact_repo.save(contact)
    audit_log_repo.append(
        build_audit_entry(
            contact.business_id,
            command.actor_id,
            AuditAction.CREATE,
            CONTACT_ENTITY,
            str(contact.id),
            now,
        )
    )
    return contact
