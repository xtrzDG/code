from app.contracts.registries import LanguageRegistryContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument, WebChatAppearance
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.sharing import HostedChatView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    PublicBaseUrl,
    WidgetScriptUrl,
)
from app.use_cases.shared.widget_languages import build_widget_languages
from app.utilities.channels.channel_endpoints import (
    WIDGET_SCRIPT_PATH,
    join_public_url,
)
from app.utilities.sharing.share_links import choose_privacy_url


class GetHostedChatUseCase(UseCaseContract[BusinessId, HostedChatView]):
    """
    What the hosted chat page (/c/{slug} on the cabinet's site) needs before
    the widget loads: the business's current address, name, colour,
    customer languages, whether the chat is on, where the widget script and
    the API live (APP_BASE_URL) and the privacy notice. The widget loads
    the rest itself, with its usual limits. Nothing personal or secret is
    returned; an unknown business is not found.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        language_registry: LanguageRegistryContract,
        app_settings: AppSettings,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._language_registry: LanguageRegistryContract = language_registry
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: BusinessId) -> HostedChatView:
        business: BusinessDocument | None = self._business_repo.get(input_data)
        if business is None:
            raise NotFoundError("This chat is not available.")

        web_chat: ChannelDocument | None = next(
            (
                channel
                for channel in self._channel_repo.list_by_business(business.id)
                if channel.kind is ChannelKind.WEB_CHAT
            ),
            None,
        )
        appearance: WebChatAppearance | None = (
            None if web_chat is None else web_chat.web_chat_appearance
        )
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        api_base_url: PublicBaseUrl | None = self._app_settings.app_base_url
        return HostedChatView(
            business_id=business.id,
            slug=business.public_slug,
            business_name=business.name,
            is_enabled=(
                web_chat is not None and web_chat.status is ChannelStatus.CONNECTED
            ),
            default_language=business.default_language,
            languages=build_widget_languages(
                self._language_registry, business.languages
            ),
            accent_color=None if appearance is None else appearance.accent_color,
            position=None if appearance is None else appearance.position,
            api_base_url=api_base_url,
            widget_script_url=(
                None
                if api_base_url is None
                else WidgetScriptUrl(
                    join_public_url(str(api_base_url), WIDGET_SCRIPT_PATH)
                )
            ),
            privacy_url=choose_privacy_url(
                business, profile, self._app_settings.cabinet_base_url
            ),
        )
