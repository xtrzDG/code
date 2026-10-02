"""Steps shared by the operations use cases (bookings, leads, handoffs):
loading tenant documents, contact updates with audit, staff messages."""

from collections.abc import Callable
from typing import NamedTuple

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.operations import StaffMessage
from app.schemas.exceptions.application_errors import (
    InvalidPhoneNumberError,
    NotFoundError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import (
    FormattedPhoneNumber,
    RawPhoneNumberInput,
)
from app.schemas.typings.users.prefixed_id import UserId

CONTACT_ENTITY: AuditEntityName = AuditEntityName("contact")


class ContactDetails(NamedTuple):
    """Name and phone a customer gave; None keeps the stored value."""

    name: ContactName | None
    phone_number: E164PhoneNumber | None


def require_business(
    business_repo: BusinessRepoContract,
    business_id: BusinessId,
) -> BusinessDocument:
    business: BusinessDocument | None = business_repo.get(business_id)
    if business is None:
        raise NotFoundError(f"Business {business_id} was not found.")

    return business


def require_contact(
    contact_repo: ContactRepoContract,
    business_id: BusinessId,
    contact_id: ContactId,
) -> ContactDocument:
    contact: ContactDocument | None = contact_repo.get(business_id, contact_id)
    if contact is None:
        raise NotFoundError(f"Contact {contact_id} was not found.")

    return contact


def display_phone(
    phone_number_parser: PhoneNumberParserContract,
    phone_number: E164PhoneNumber | None,
) -> FormattedPhoneNumber | None:
    """
    International format ("+995 555 12 34 56") of a stored E.164 number; the
    E.164 form itself when the numbering plan no longer accepts it.
    """

    if phone_number is None:
        return None

    try:
        return phone_number_parser.parse(
            RawPhoneNumberInput(str(phone_number)), None
        ).international_format
    except InvalidPhoneNumberError:
        return FormattedPhoneNumber(str(phone_number))


def update_contact_details(
    contact_repo: ContactRepoContract,
    audit_log_repo: AuditLogRepoContract,
    contact: ContactDocument,
    details: ContactDetails,
    actor_id: UserId | None,
    now: Microseconds,
) -> ContactDocument:
    """
    Store a changed name or phone of a contact and audit the change of
    personal data (actor None: the assistant during a conversation).
    """

    is_changed: bool = False
    if details.name is not None and details.name != contact.name:
        contact.name = details.name
        is_changed = True

    if (
        details.phone_number is not None
        and details.phone_number != contact.phone_number
    ):
        contact.phone_number = details.phone_number
        is_changed = True

    if not is_changed:
        return contact

    contact.updated_at = now
    contact_repo.save(contact)
    audit_log_repo.append(
        build_audit_entry(
            contact.business_id,
            actor_id,
            AuditAction.UPDATE,
            CONTACT_ENTITY,
            str(contact.id),
            now,
        )
    )
    return contact


def build_audit_entry(
    business_id: BusinessId,
    actor_id: UserId | None,
    action: AuditAction,
    entity: AuditEntityName,
    entity_reference: str | None,
    now: Microseconds,
) -> AuditLogEntryDocument:
    return AuditLogEntryDocument(
        business_id=business_id,
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=(
            None if entity_reference is None else AuditEntityReference(entity_reference)
        ),
        created_at=now,
        updated_at=now,
    )


def build_staff_messages(
    business: BusinessDocument,
    render_for_language: Callable[[LanguageTag], MessageText],
) -> list[StaffMessage]:
    """One message per manager contact, rendered once per language."""

    texts: dict[LanguageTag, MessageText] = {}
    messages: list[StaffMessage] = []
    for manager_contact in business.manager_contacts:
        text: MessageText | None = texts.get(manager_contact.language)
        if text is None:
            text = render_for_language(manager_contact.language)
            texts[manager_contact.language] = text

        messages.append(StaffMessage(contact=manager_contact, text=text))

    return messages
