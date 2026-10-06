"""
Read-only catalogs for prices in local currencies, call forwarding and the
owner-facing texts in every cabinet language.
"""

from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.constants.localization import CabinetLanguage, TextReviewStatus
from app.schemas.dto.catalog.call_forwarding import CallForwardingGuide
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    OwnerTextKey,
)


class ExchangeRateRegistryContract(RegistryContract, Protocol):
    def find_rate(
        self,
        base_currency_code: CurrencyCode,
        quote_currency_code: CurrencyCode,
    ) -> ExchangeRateQuote | None:
        """
        The newest rate base -> quote: a published one, else its inverse,
        else a cross rate through the euro (both marked derived); None when
        no bank publishes either currency. Rates are never invented.
        """
        raise NotImplementedError


class CallForwardingGuideRegistryContract(RegistryContract, Protocol):
    def get(self, country_code: CountryCode) -> CallForwardingGuide:
        """
        Forwarding guide for a country: named carriers where they are known,
        standard GSM codes everywhere else.
        """
        raise NotImplementedError


class TextCatalogRegistryContract(RegistryContract, Protocol):
    def get(self, key: OwnerTextKey) -> LocalizedText:
        """
        The owner-facing text of a key in every cabinet language that has it
        (English always).

        Raises:
            TextCatalogError: the catalog has no such key.
        """
        raise NotImplementedError

    def list_keys(self) -> list[OwnerTextKey]:
        """Every key of the catalog, in the order of the English source."""
        raise NotImplementedError

    def list_missing_keys(self, language: CabinetLanguage) -> list[OwnerTextKey]:
        """Keys a language has no text for yet (they read English)."""
        raise NotImplementedError

    def review_status(
        self, key: OwnerTextKey, language: CabinetLanguage
    ) -> TextReviewStatus | None:
        """
        Whether a language's text of a key was checked by a native speaker;
        None when the language has no text for it.
        """
        raise NotImplementedError
