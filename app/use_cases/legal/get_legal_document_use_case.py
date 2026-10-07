from typed_time_provider import Microseconds, WallClock

from app.contracts.legal_text_registries import LegalTextRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.legal import LegalDocumentQuery, LegalDocumentView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.cldr_language_names import ENGLISH_LOCALE_IDENTIFIER


class GetLegalDocumentUseCase(UseCaseContract[LegalDocumentQuery, LegalDocumentView]):
    """
    GET /v1/legal/{terms|privacy|cookies|security} (public): the version
    in force today, or the version asked for (an owner rereads what they
    accepted), in the language asked for, else its base language, else
    English. The public pages and the sign-in page's acceptance line read
    it; it is a draft while it has open fields or the operator has not set
    LEGAL_TEXTS_FINAL.

    Raises:
        NotFoundError: no text of that version, or none in force yet.
    """

    def __init__(
        self,
        legal_text_registry: LegalTextRegistryContract,
        wall_clock: WallClock[Microseconds],
        app_settings: AppSettings,
    ) -> None:
        self._registry: LegalTextRegistryContract = legal_text_registry
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: LegalDocumentQuery) -> LegalDocumentView:
        document: LegalDocumentView | None = self._registry.find(
            input_data.kind,
            input_data.version,
            input_data.language or LanguageTag(ENGLISH_LOCALE_IDENTIFIER),
            self._wall_clock.now_unix(),
        )
        if document is None:
            raise NotFoundError(
                f"There is no {input_data.kind.value} text"
                + (f" of version {input_data.version}." if input_data.version else ".")
            )

        are_final: bool = self._app_settings.public_site.are_legal_texts_final
        return document.model_copy(
            update={"is_draft": document.has_placeholders or not are_final}
        )
