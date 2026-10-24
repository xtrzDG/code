from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.messaging_clients import SmsMessagingClientContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.call_follow_up_repositories import (
    CallSettingsRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.calls.call_settings import (
    CallSettingsView,
    UpdateCallSettingsCommand,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.voice.call_settings.call_settings_views import (
    build_call_settings_view,
    stored_or_default,
)

CALL_SETTINGS_ENTITY: AuditEntityName = AuditEntityName("call_settings")


class UpdateCallSettingsUseCase(
    UseCaseContract[UpdateCallSettingsCommand, CallSettingsView]
):
    """
    The owner turns call summaries and text-backs on or off, names the
    approved WhatsApp template and allows the SMS fallback. A text-back
    can be on without a template or SMS: it then skips every caller with
    "no channel", which the list of text-backs shows. Audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        call_settings_repo: CallSettingsRepoContract,
        channel_repo: ChannelRepoContract,
        audit_log_repo: AuditLogRepoContract,
        text_resolver: LocalizedTextResolverContract,
        sms_client: SmsMessagingClientContract | None,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._call_settings_repo: CallSettingsRepoContract = call_settings_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._text_resolver: LocalizedTextResolverContract = text_resolver
        self._is_sms_available: bool = sms_client is not None
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateCallSettingsCommand) -> CallSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        settings: CallSettingsDocument = stored_or_default(
            business, self._call_settings_repo.get_by_business(business.id)
        )
        request = input_data.request
        settings.is_summary_enabled = request.is_summary_enabled
        settings.is_text_back_enabled = request.is_text_back_enabled
        settings.text_back_template_name = request.text_back_template_name
        settings.is_sms_fallback_enabled = request.is_sms_fallback_enabled
        settings.updated_at = now
        self._call_settings_repo.save(settings)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=CALL_SETTINGS_ENTITY,
                entity_id=AuditEntityReference(str(settings.id)),
                created_at=now,
                updated_at=now,
            )
        )
        return build_call_settings_view(
            business,
            settings,
            self._channel_repo,
            self._text_resolver,
            self._is_sms_available,
        )
