from app.contracts.registries import LanguageRegistryContract
from app.contracts.repositories import BusinessRepoContract, ChannelRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels import WidgetConfigView, WidgetLanguageView
from app.schemas.dto.localization import LanguageProfile
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    UnsupportedLanguageError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.channels.delivery_targets import find_business_channel


class GetWidgetConfigUseCase(UseCaseContract[BusinessId, WidgetConfigView]):
    """
    Public configuration of a business's website chat widget: name, customer
    languages with their native names and writing direction (right-to-left
    for Hebrew, Arabic, ...), default language, and whether the owner has
    switched the widget on. Nothing personal or secret is returned.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        language_registry: LanguageRegistryContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
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
        languages: list[WidgetLanguageView] = []
        for language_tag in business.languages:
            try:
                profile: LanguageProfile = self._language_registry.get(language_tag)
            except UnsupportedLanguageError:
                continue

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
        )
