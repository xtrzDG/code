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
