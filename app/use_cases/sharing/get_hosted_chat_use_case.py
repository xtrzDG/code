from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import LanguageRegistryContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.retention_repositories import (
    BusinessPrivacySettingsRepoContract,
)
from app.contracts.repositories.setup_repositories import SetupStateRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument, WebChatAppearance
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.setup import SetupStateDocument
from app.schemas.dto.sharing import HostedChatView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    PublicBaseUrl,
    WidgetScriptUrl,
)
from app.use_cases.shared.widget_languages import build_widget_languages
from app.utilities.bookings.booking_manage_links import choose_maps_url
from app.utilities.channels.channel_endpoints import (
    WIDGET_SCRIPT_PATH,
    join_public_url,
)
from app.utilities.knowledge.profile_links import find_profile_link
from app.utilities.sharing.share_links import choose_privacy_url


class GetHostedChatUseCase(UseCaseContract[BusinessId, HostedChatView]):
    """
    What the hosted chat page (/c/{slug} on the cabinet's site) needs before
    the widget loads: the business's current address, name, colour,
    customer languages, whether the chat is on, where the widget script and
    the API live (APP_BASE_URL) and the privacy notice, with the retention
    periods the business chose in Settings → Privacy. For a "link in bio"
    page it adds the business's hours, address with a map link and whether
    it takes bookings (and its own booking page, if any). The widget loads
    the rest itself, with its usual limits. Nothing personal or secret is
    returned; an unknown business is not found.

    The first visit to the page of a live business is noted in its setup
    state (the guide's "Show customers where to write" step; the day-10
    reminder is not needed then). Later visits change nothing.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        language_registry: LanguageRegistryContract,
        setup_state_repo: SetupStateRepoContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        privacy_settings_repo: BusinessPrivacySettingsRepoContract,
    ) -> None:
        self._privacy_settings_repo: BusinessPrivacySettingsRepoContract = (
            privacy_settings_repo
        )
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._language_registry: LanguageRegistryContract = language_registry
        self._setup_state_repo: SetupStateRepoContract = setup_state_repo
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

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
        is_enabled: bool = (
            web_chat is not None and web_chat.status is ChannelStatus.CONNECTED
        )
        if is_enabled and business.published_assistant_version_id is not None:
            self._note_first_visit(business)

        retention: BusinessPrivacySettingsDocument = (
            self._privacy_settings_repo.get_or_default(business.id)
        )
        return HostedChatView(
            business_id=business.id,
            slug=business.public_slug,
            business_name=business.name,
            is_enabled=is_enabled,
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
            conversation_retention_days=retention.conversation_retention_days,
            llm_turn_retention_days=retention.llm_turn_retention_days,
            timezone=business.timezone,
            hours=[] if profile is None else list(profile.hours),
            address=(
                None
                if profile is None or profile.address is None
                else profile.address.text
            ),
            maps_url=None if profile is None else choose_maps_url(profile.address),
            takes_bookings=profile is not None and profile.booking_rules is not None,
            booking_url=(
                None
                if profile is None
                else find_profile_link(profile, BusinessLinkKind.BOOKING_PAGE)
            ),
        )

    def _note_first_visit(self, business: BusinessDocument) -> None:
        stored: SetupStateDocument | None = self._setup_state_repo.get_by_business(
            business.id
        )
        if stored is not None and stored.hosted_page_visited_at is not None:
            return

        now: Microseconds = self._wall_clock.now_unix()

        def note(state: SetupStateDocument) -> None:
            if state.hosted_page_visited_at is None:
                state.hosted_page_visited_at = now

        self._setup_state_repo.change(business.id, note, now)
