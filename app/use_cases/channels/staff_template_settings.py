"""
Storing the WhatsApp templates for staff replies (one per language) on the
business's WhatsApp channel, shared by the single-template and the
per-language endpoints.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument, WhatsAppStaffTemplate
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.staff_reply_templates import WhatsAppStaffTemplateEntry
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.staff_templates import fallback_staff_template

CHANNEL_ENTITY: AuditEntityName = AuditEntityName("channel")
DUPLICATE_LANGUAGE_REASON: ErrorReasonCode = ErrorReasonCode(
    "duplicate_template_language"
)


def read_template_entries(
    entries: Sequence[WhatsAppStaffTemplateEntry],
) -> list[WhatsAppStaffTemplate]:
    """
    The templates in the order given; ValidationFailedError (reason
    `duplicate_template_language`, the repeated codes as details) when two
    share a language: a reply in that language could take either.
    """

    seen: set[str] = set()
    repeated: list[str] = []
    for entry in entries:
        code: str = str(entry.language_code)
        if code in seen and code not in repeated:
            repeated.append(code)
        seen.add(code)

    if repeated:
        raise ValidationFailedError(
            "Each template language may appear once.",
            reasons=[
                ErrorReason(
                    code=DUPLICATE_LANGUAGE_REASON,
                    message=ErrorReasonMessage("Two templates name the same language."),
                    details=[ErrorReasonDetail(code) for code in repeated],
                )
            ],
        )

    return [
        WhatsAppStaffTemplate(name=entry.name, language_code=entry.language_code)
        for entry in entries
    ]


def store_staff_templates(
    channel_repo: ChannelRepoContract,
    business: BusinessDocument,
    templates: Sequence[WhatsAppStaffTemplate],
    now: Microseconds,
) -> ChannelDocument:
    """
    Replace the templates of the business's WhatsApp channel in one step
    (a concurrent health update is kept), with the single template the
    previous release reads; NotFoundError when WhatsApp was never connected.
    """

    channel: ChannelDocument | None = find_business_channel(
        channel_repo, business.id, ChannelKind.WHATSAPP
    )
    if channel is None:
        raise NotFoundError("The whatsapp channel is not connected.")

    def change(current: ChannelDocument) -> ChannelDocument:
        current.whatsapp_staff_templates = list(templates)
        current.whatsapp_staff_template = fallback_staff_template(
            templates, business.default_language
        )
        current.updated_at = now
        return current

    stored: ChannelDocument | None = channel_repo.modify(
        business.id, channel.id, change
    )
    if stored is None:
        raise NotFoundError("The whatsapp channel is not connected.")

    return stored


def audit_template_change(
    audit_log_repo: AuditLogRepoContract,
    channel: ChannelDocument,
    actor_id: UserId,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """The change of the channel's templates in the audit log."""

    audit_log_repo.append(
        AuditLogEntryDocument(
            business_id=channel.business_id,
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            entity=CHANNEL_ENTITY,
            entity_id=AuditEntityReference(str(channel.id)),
            ip_address=client_ip_address,
            created_at=now,
            updated_at=now,
        )
    )
