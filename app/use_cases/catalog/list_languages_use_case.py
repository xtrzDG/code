from babel import Locale

from app.contracts.registries import LanguageRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.catalog.countries import (
    LanguageList,
    LanguageListItem,
    LanguageListRequest,
)
from app.utilities.localization.display_names import (
    build_language_display_name_or_tag,
)
from app.utilities.localization.language_tags import require_babel_locale


class ListLanguagesUseCase(UseCaseContract[LanguageListRequest, LanguageList]):
    """
    Languages an owner can switch on for customers, with honest text and
    voice support levels, named in the display language and ordered by that
    name.
    """

    def __init__(self, language_registry: LanguageRegistryContract) -> None:
        self._language_registry: LanguageRegistryContract = language_registry

    def run(self, input_data: LanguageListRequest) -> LanguageList:
        display_locale: Locale = require_babel_locale(input_data.display_language)
        languages: list[LanguageListItem] = [
            LanguageListItem(
                profile=profile,
                display_name=build_language_display_name_or_tag(
                    profile.tag,
                    display_locale,
                ),
            )
            for profile in self._language_registry.list_all()
        ]
        return LanguageList(
            display_language=input_data.display_language,
            languages=sorted(
                languages,
                key=lambda language: (
                    language.display_name.casefold(),
                    str(language.profile.tag),
                ),
            ),
        )
