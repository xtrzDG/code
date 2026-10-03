from app.contracts.localization_utilities import LanguageDetectorContract
from app.contracts.registries import LanguageRegistryContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument, WebChatAppearance
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.channels.widget import WidgetConfigView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.channels.widget_languages import (
    build_widget_greetings,
    build_widget_languages,
)
from app.utilities.channels.widget_starters import build_starter_questions
from app.utilities.sharing.share_links import build_contact_links, choose_privacy_url

# The first FAQ items read for starter questions: enough for three per
# language after inactive and imported drafts are left out.
FAQ_ITEMS_READ_FOR_STARTERS: DocumentQueryLimit = DocumentQueryLimit(30)


class GetWidgetConfigUseCase(UseCaseContract[BusinessId, WidgetConfigView]):
    """
    Public configuration of a business's website chat widget: name, customer
    languages with their native names and writing direction (right-to-left
    for Hebrew, Arabic, ...), default language, whether the owner has
    switched the widget on, the owner's colour and launcher corner, the
    greeting in each language the live assistant answers in (the business
    languages before a version is published), up to three starter
    questions per language from the FAQ, the privacy notice the footer
    links to, and the business's other channels (the hosted chat page
    offers them). Nothing personal or secret is returned.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        language_registry: LanguageRegistryContract,
        language_detector: LanguageDetectorContract,
        app_settings: AppSettings,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._language_registry: LanguageRegistryContract = language_registry
        self._language_detector: LanguageDetectorContract = language_detector
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: BusinessId) -> WidgetConfigView:
        business: BusinessDocument | None = self._business_repo.get(input_data)
        if business is None:
            raise NotFoundError("This chat is not available.")

        channels: list[ChannelDocument] = self._channel_repo.list_by_business(
            business.id
        )
        web_chat: ChannelDocument | None = next(
            (channel for channel in channels if channel.kind is ChannelKind.WEB_CHAT),
            None,
        )
        appearance: WebChatAppearance | None = (
            None if web_chat is None else web_chat.web_chat_appearance
        )
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        assistant_languages: list[LanguageTag] = self._assistant_languages(business)
        return WidgetConfigView(
            business_id=business.id,
            business_name=business.name,
            is_enabled=(
                web_chat is not None and web_chat.status is ChannelStatus.CONNECTED
            ),
            default_language=business.default_language,
            languages=build_widget_languages(
                self._language_registry, business.languages
            ),
            greetings=build_widget_greetings(
                self._language_registry, assistant_languages, business.name
            ),
            accent_color=None if appearance is None else appearance.accent_color,
            position=None if appearance is None else appearance.position,
            starter_questions=build_starter_questions(
                self._knowledge_item_repo.list_by_kind(
                    business.id, KnowledgeItemKind.FAQ, FAQ_ITEMS_READ_FOR_STARTERS
                ),
                assistant_languages,
                business.default_language,
                self._language_detector,
            ),
            privacy_url=choose_privacy_url(
                business, profile, self._app_settings.cabinet_base_url
            ),
            contact_links=build_contact_links(channels, profile),
        )

    def _assistant_languages(self, business: BusinessDocument) -> list[LanguageTag]:
        """The published version's languages, else the business languages."""

        if business.published_assistant_version_id is None:
            return list(business.languages)

        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business.id, business.published_assistant_version_id
        )
        return list(business.languages if version is None else version.languages)
