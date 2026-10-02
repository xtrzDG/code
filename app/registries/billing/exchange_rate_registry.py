from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.registries.billing.exchange_rate_catalog import OFFICIAL_EXCHANGE_RATES
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.typings.localization.constrained_strings import CurrencyCode


class ExchangeRateRegistry(ExchangeRateRegistryContract):
    """
    Official rates with their source and date (concept: NBG EUR -> GEL).

    Only direct pairs are answered; an inverse or cross rate would be a new
    number nobody published.
    """

    def __init__(
        self,
        exchange_rates: tuple[ExchangeRateQuote, ...] = OFFICIAL_EXCHANGE_RATES,
    ) -> None:
        self._exchange_rates: tuple[ExchangeRateQuote, ...] = exchange_rates

    def find_rate(
        self,
        base_currency_code: CurrencyCode,
        quote_currency_code: CurrencyCode,
    ) -> ExchangeRateQuote | None:
        for exchange_rate in self._exchange_rates:
            if (
                exchange_rate.base_currency_code == base_currency_code
                and exchange_rate.quote_currency_code == quote_currency_code
            ):
                return exchange_rate

        return None

    def list_all(self) -> list[ExchangeRateQuote]:
        return list(self._exchange_rates)
