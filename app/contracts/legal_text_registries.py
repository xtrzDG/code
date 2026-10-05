"""The platform's own legal texts for owners: terms, privacy policy, cookies."""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.registry_contract import RegistryContract
from app.schemas.constants.legal import LegalDocumentKind
from app.schemas.dto.legal import LegalDocumentView
from app.schemas.typings.legal.constrained_strings import LegalDocumentVersion
from app.schemas.typings.localization.constrained_strings import LanguageTag


class LegalTextRegistryContract(RegistryContract, Protocol):
    def version_in_force(
        self, kind: LegalDocumentKind, now: Microseconds
    ) -> LegalDocumentVersion | None:
        """
        The newest version that took effect by `now` (its UTC day); None
        before the first one.
        """
        raise NotImplementedError

    def has_version(
        self, kind: LegalDocumentKind, version: LegalDocumentVersion
    ) -> bool:
        """True when that version has a text in this build."""
        raise NotImplementedError

    def find(
        self,
        kind: LegalDocumentKind,
        version: LegalDocumentVersion | None,
        language: LanguageTag,
        now: Microseconds,
    ) -> LegalDocumentView | None:
        """
        One version's text (the one in force when `version` is None) in the
        language asked for, else its base language, else English; with the
        newer version already published, if any. None when there is no such
        text.
        """
        raise NotImplementedError
