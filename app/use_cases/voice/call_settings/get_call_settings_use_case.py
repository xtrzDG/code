from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.messaging_clients import SmsMessagingClientContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.call_follow_up_repositories import (
    CallSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.calls.call_settings import CallSettingsQuery, CallSettingsView
from app.use_cases.voice.call_settings.call_settings_views import (
    build_call_settings_view,
    stored_or_default,
)


class GetCallSettingsUseCase(UseCaseContract[CallSettingsQuery, CallSettingsView]):
    """
    Settings → Calls for the owner: summaries and text-backs on or off, the
    WhatsApp template's name, the SMS fallback, whether the WhatsApp number
    is connected and SMS can be sent, and the text-back to register as the
    template in each of the business's languages.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        call_settings_repo: CallSettingsRepoContract,
        channel_repo: ChannelRepoContract,
        text_resolver: LocalizedTextResolverContract,
        sms_client: SmsMessagingClientContract | None,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._call_settings_repo: CallSettingsRepoContract = call_settings_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._text_resolver: LocalizedTextResolverContract = text_resolver
        self._is_sms_available: bool = sms_client is not None

    def run(self, input_data: CallSettingsQuery) -> CallSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        return build_call_settings_view(
            business,
            stored_or_default(
                business, self._call_settings_repo.get_by_business(business.id)
            ),
            self._channel_repo,
            self._text_resolver,
            self._is_sms_available,
        )
