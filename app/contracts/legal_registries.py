"""Read-only texts of legal documents shipped with the product."""

from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.dto.compliance import DpaDocumentView
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.localization.constrained_strings import LanguageTag


class LegalDocumentRegistryContract(RegistryContract, Protocol):
    def find_dpa(
        self,
        version: DpaDocumentVersion,
        language: LanguageTag,
    ) -> DpaDocumentView | None:
        """
        The data processing agreement of a version in the language asked
        for, else its base language, else English, else any translation;
        None when the version has no text at all.
        """
        raise NotImplementedError
