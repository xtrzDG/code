from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument, WhatsAppStaffTemplate
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.staff_reply_templates import (
    SetWhatsAppStaffTemplateCommand,
    WhatsAppStaffTemplateRequest,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.channels.channel_views import build_channel_view
from app.utilities.channels.delivery_targets import find_business_channel

CHANNEL_ENTITY: AuditEntityName = AuditEntityName("channel")


class SetWhatsAppStaffTemplateUseCase(
    UseCaseContract[SetWhatsAppStaffTemplateCommand, ChannelView]
):
    """
    Owner names the Meta-approved message template that carries staff
    replies on WhatsApp once the customer's 24-hour window has closed
    (concept section 6): its name and approved language. The template's
    body must have exactly one parameter; the staff text goes into it.
    Neither field removes the template, and staff replies outside the
    window are refused again.

    The setting belongs to the business's WhatsApp channel (kept while the
    channel is switched off); a business that never connected WhatsApp has
    nothing to set. The change is written to the audit log.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        channel_repo: ChannelRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._channel_repo: ChannelRepoContract = channel_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SetWhatsAppStaffTemplateCommand) -> ChannelView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        template: WhatsAppStaffTemplate | None = read_staff_template(input_data.request)
        channel: ChannelDocument | None = find_business_channel(
            self._channel_repo,
            business.id,
            ChannelKind.WHATSAPP,
        )
        if channel is None:
            raise NotFoundError("The whatsapp channel is not connected.")

        now: Microseconds = self._wall_clock.now_unix()
        channel.whatsapp_staff_template = template
        channel.updated_at = now
        self._channel_repo.save(channel)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=CHANNEL_ENTITY,
                entity_id=AuditEntityReference(str(channel.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return build_channel_view(channel)


def read_staff_template(
    request: WhatsAppStaffTemplateRequest,
) -> WhatsAppStaffTemplate | None:
    """Both fields set a template, neither removes it; one alone is refused."""

    if request.name is None and request.language_code is None:
        return None

    if request.name is None or request.language_code is None:
        raise ValidationFailedError(
            "name and language_code of the template are needed together."
        )

    return WhatsAppStaffTemplate(
        name=request.name,
        language_code=request.language_code,
    )
