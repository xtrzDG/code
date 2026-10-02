from app.contracts.registries import LanguageRegistryContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.localization import TextDirection
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument, WebChatAppearance
from app.schemas.dto.channels import (
    WidgetConfigView,
    WidgetGreetingView,
    WidgetLanguageView,
)
from app.schemas.dto.localization import LanguageProfile
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    UnsupportedLanguageError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import WidgetGreetingText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.widget_texts import build_widget_greeting


class GetWidgetConfigUseCase(UseCaseContract[BusinessId, WidgetConfigView]):
    """
    Public configuration of a business's website chat widget: name, customer
    languages with their native names and writing direction (right-to-left
    for Hebrew, Arabic, ...), default language, whether the owner has
    switched the widget on, the owner's colour and launcher corner, and the
    greeting in each language the live assistant answers in (the business
    languages before a version is published). Nothing personal or secret is
    returned.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        language_registry: LanguageRegistryContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._language_registry: LanguageRegistryContract = language_registry

    def run(self, input_data: BusinessId) -> WidgetConfigView:
        business: BusinessDocument | None = self._business_repo.get(input_data)
        if business is None:
            raise NotFoundError("This chat is not available.")

        channel: ChannelDocument | None = find_business_channel(
            self._channel_repo,
            business.id,
            ChannelKind.WEB_CHAT,
        )
        appearance: WebChatAppearance | None = (
            None if channel is None else channel.web_chat_appearance
        )
        languages: list[WidgetLanguageView] = []
        for language_tag in business.languages:
            profile: LanguageProfile | None = self._find_language(language_tag)
            if profile is not None:
                languages.append(
                    WidgetLanguageView(
                        tag=language_tag,
                        native_name=profile.native_name,
                        direction=profile.direction,
                    )
                )

        return WidgetConfigView(
            business_id=business.id,
            business_name=business.name,
            is_enabled=(
                channel is not None and channel.status is ChannelStatus.CONNECTED
            ),
            default_language=business.default_language,
            languages=languages,
            greetings=self._build_greetings(business),
            accent_color=None if appearance is None else appearance.accent_color,
            position=None if appearance is None else appearance.position,
        )

    def _build_greetings(self, business: BusinessDocument) -> list[WidgetGreetingView]:
        greetings: list[WidgetGreetingView] = []
        for language_tag in self._assistant_languages(business):
            text: str | None = build_widget_greeting(language_tag, str(business.name))
            if text is None:
                continue

            profile: LanguageProfile | None = self._find_language(language_tag)
            greetings.append(
                WidgetGreetingView(
                    language=language_tag,
                    text=WidgetGreetingText(text),
                    direction=(
                        TextDirection.LEFT_TO_RIGHT
                        if profile is None
                        else profile.direction
                    ),
                )
            )

        return greetings

    def _assistant_languages(self, business: BusinessDocument) -> list[LanguageTag]:
        """The published version's languages, else the business languages."""

        if business.published_assistant_version_id is None:
            return list(business.languages)

        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business.id, business.published_assistant_version_id
        )
        return list(business.languages if version is None else version.languages)

    def _find_language(self, language_tag: LanguageTag) -> LanguageProfile | None:
        try:
            return self._language_registry.get(language_tag)
        except UnsupportedLanguageError:
            return None
