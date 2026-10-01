from app.contracts.legal_registries import LegalDocumentRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.compliance import DpaDocumentQuery, DpaDocumentView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import ENGLISH_LOCALE_IDENTIFIER


class GetDpaDocumentUseCase(UseCaseContract[DpaDocumentQuery, DpaDocumentView]):
    """
    The text of one data processing agreement version, so an owner reads
    what they accept (and anyone can read the template before signing up).
    The language falls back to the base language, then English.
    """

    def __init__(self, legal_document_registry: LegalDocumentRegistryContract) -> None:
        self._legal_document_registry: LegalDocumentRegistryContract = (
            legal_document_registry
        )

    def run(self, input_data: DpaDocumentQuery) -> DpaDocumentView:
        document: DpaDocumentView | None = self._legal_document_registry.find_dpa(
            input_data.version,
            input_data.language or LanguageTag(ENGLISH_LOCALE_IDENTIFIER),
        )
        if document is None:
            raise NotFoundError(
                f"The data processing agreement {input_data.version} has no text."
            )

        return document
