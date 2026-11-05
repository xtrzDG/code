from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument, WhatsAppStaffTemplate
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.staff_reply_templates import SetWhatsAppStaffTemplatesCommand
from app.use_cases.channels.channel_views import build_channel_view
from app.use_cases.channels.staff_template_settings import (
    audit_template_change,
    read_template_entries,
    store_staff_templates,
)


class SetWhatsAppStaffTemplatesUseCase(
    UseCaseContract[SetWhatsAppStaffTemplatesCommand, ChannelView]
):
    """
    Owner replaces the Meta-approved templates that carry staff replies on
    WhatsApp once the customer's 24-hour window has closed, one per
    template language (e.g. "staff_reply" approved in Georgian and
    "staff_reply_he" in Hebrew). A reply takes the template of the
    conversation's language, then the business's default language
    (`app/utilities/channels/staff_templates.py`), so a Hebrew customer no
    longer gets the staff text inside a Russian template. Two templates of
    one language are refused (422, reason `duplicate_template_language`);
    an empty list removes them all.

    Owners only, on a business that connected WhatsApp at least once; the
    change is written to the audit log.
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

    def run(self, input_data: SetWhatsAppStaffTemplatesCommand) -> ChannelView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        templates: list[WhatsAppStaffTemplate] = read_template_entries(
            input_data.request.templates
        )
        now: Microseconds = self._wall_clock.now_unix()
        channel: ChannelDocument = store_staff_templates(
            self._channel_repo, business, templates, now
        )
        audit_template_change(
            self._audit_log_repo,
            channel,
            input_data.user_id,
            input_data.client_ip_address,
            now,
        )
        return build_channel_view(channel)
