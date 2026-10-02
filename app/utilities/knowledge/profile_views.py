"""Profile documents, their owner-facing views and their audit entries."""

from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.profiles import BusinessContacts, BusinessProfileDocument
from app.schemas.dto.profiles.business_profile import BusinessProfileView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.users.prefixed_id import UserId

CONTACTS_AUDIT_ENTITY: AuditEntityName = AuditEntityName("business_profile.contacts")


def new_profile(
    business: BusinessDocument, now: Microseconds
) -> BusinessProfileDocument:
    """
    An empty profile for a business that has not saved one yet.

    Answers are written in the owner's language until the owner picks another.
    """

    return BusinessProfileDocument(
        business_id=business.id,
        niche_key=business.niche_key,
        answers_language=business.owner_language,
        created_at=now,
        updated_at=now,
    )


def to_profile_view(
    business: BusinessDocument,
    profile: BusinessProfileDocument | None,
) -> BusinessProfileView:
    """The saved profile, or a blank one before the first save."""

    if profile is None:
        return BusinessProfileView(
            business_id=business.id,
            niche_key=business.niche_key,
            answers_language=business.owner_language,
            contacts=BusinessContacts(),
            is_recording_notice_enabled=True,
            is_saved=False,
        )

    return BusinessProfileView(
        business_id=profile.business_id,
        niche_key=business.niche_key,
        answers_language=profile.answers_language,
        address=profile.address,
        hours=list(profile.hours),
        contacts=profile.contacts,
        booking_rules=profile.booking_rules,
        handoff_rules=list(profile.handoff_rules),
        forbidden=list(profile.forbidden),
        tone=profile.tone,
        links=list(profile.links),
        niche_answers=list(profile.niche_answers),
        is_recording_notice_enabled=profile.is_recording_notice_enabled,
        is_saved=True,
        updated_at=profile.updated_at,
    )


def build_contacts_audit_entry(
    business_id: BusinessId,
    actor_id: UserId,
    now: Microseconds,
) -> AuditLogEntryDocument:
    """
    Audit entry for a change of the profile phones.

    Handoff phones are often a manager's personal mobile, so changing them
    is an operation on personal data.
    """

    return AuditLogEntryDocument(
        business_id=business_id,
        actor_id=actor_id,
        action=AuditAction.UPDATE,
        entity=CONTACTS_AUDIT_ENTITY,
        entity_id=AuditEntityReference(str(business_id)),
        created_at=now,
        updated_at=now,
    )
