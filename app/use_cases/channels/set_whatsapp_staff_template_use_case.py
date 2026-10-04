from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument, WhatsAppStaffTemplate
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.staff_reply_templates import (
    SetWhatsAppStaffTemplateCommand,
    WhatsAppStaffTemplateRequest,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.use_cases.channels.channel_views import build_channel_view
from app.use_cases.channels.staff_template_settings import (
    audit_template_change,
    store_staff_templates,
)


class SetWhatsAppStaffTemplateUseCase(
    UseCaseContract[SetWhatsAppStaffTemplateCommand, ChannelView]
):
    """
    Owner names the one Meta-approved message template that carries staff
    replies on WhatsApp once the customer's 24-hour window has closed
    (concept section 6): its name and approved language. The template's
    body must have exactly one parameter; the staff text goes into it.
    Neither field removes it, and staff replies outside the window are
    refused again.

    The single-template form of `SetWhatsAppStaffTemplatesUseCase` (one per
    language): the channel's templates become this one, or none. The
    setting belongs to the business's WhatsApp channel (kept while the
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
        now: Microseconds = self._wall_clock.now_unix()
        channel: ChannelDocument = store_staff_templates(
            self._channel_repo,
            business,
            [] if template is None else [template],
            now,
        )
        audit_template_change(
            self._audit_log_repo,
            channel,
            input_data.user_id,
            input_data.client_ip_address,
            now,
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
