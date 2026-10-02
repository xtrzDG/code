"""Read-only catalogs for prices in local currencies and call forwarding."""

from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.dto.catalog.call_forwarding import CallForwardingGuide
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
)


class ExchangeRateRegistryContract(RegistryContract, Protocol):
    def find_rate(
        self,
        base_currency_code: CurrencyCode,
        quote_currency_code: CurrencyCode,
    ) -> ExchangeRateQuote | None:
        """Official rate base -> quote, or None; rates are never invented."""
        raise NotImplementedError

    def list_all(self) -> list[ExchangeRateQuote]:
        raise NotImplementedError


class CallForwardingGuideRegistryContract(RegistryContract, Protocol):
    def get(self, country_code: CountryCode) -> CallForwardingGuide:
        """
        Forwarding guide for a country: named carriers where they are known,
        standard GSM codes everywhere else.
        """
        raise NotImplementedError
