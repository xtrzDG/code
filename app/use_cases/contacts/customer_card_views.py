"""The card view a change answers with, and the audit entry of a card change."""

from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.customer_settings import CustomerSettingsDocument
from app.schemas.dto.customers.customer_card import CustomerCardView
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.customers.customer_card import tag_values

CONTACT_ENTITY: AuditEntityName = AuditEntityName("contact")


def card_view(
    contact: ContactDocument, settings: CustomerSettingsDocument | None
) -> CustomerCardView:
    return CustomerCardView(
        contact_id=contact.id,
        tags=tag_values(contact),
        is_vip=contact.is_vip,
        is_blocked=contact.block is not None,
        blocked_at=None if contact.block is None else contact.block.blocked_at,
        known_tags=[] if settings is None else list(settings.known_tags),
    )


def card_change_entry(
    contact: ContactDocument,
    actor_id: UserId,
    ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> AuditLogEntryDocument:
    """An UPDATE of the contact: who changed the card of whom, and when."""

    return AuditLogEntryDocument(
        business_id=contact.business_id,
        actor_id=actor_id,
        action=AuditAction.UPDATE,
        entity=CONTACT_ENTITY,
        entity_id=AuditEntityReference(str(contact.id)),
        ip_address=ip_address,
        created_at=now,
        updated_at=now,
    )
