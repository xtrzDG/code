"""
What the phone line use cases look up: the business's answering voice
agent, its phone channel, and the owner's price of a kind of number.
"""

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.schemas.configurations.phone_number_settings import PhoneNumberSettings
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.dto.billing import Money
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.telephony.rental_prices import CARRIER_CURRENCY, price_rental


def find_answering_agent(
    assistant_version_repo: AssistantVersionRepoContract, business_id: BusinessId
) -> VoiceAgentId | None:
    """
    The voice agent of the business's published version: the one that
    answers its calls (None: not live, or live without voice).
    """

    for version in assistant_version_repo.list_by_business(business_id):
        if version.status is AssistantVersionStatus.PUBLISHED:
            return version.voice_agent_id

    return None


def quote_owner_price(
    monthly_cost: CostMicroUsd,
    settings: PhoneNumberSettings,
    currency_code: CurrencyCode,
    exchange_rate_registry: ExchangeRateRegistryContract,
) -> Money:
    """
    The carrier's monthly price with the platform's markup in the business's
    currency (the official rate of the day), rounded up to a whole unit; in
    dollars when no bank publishes a rate for that currency.
    """

    rate: ExchangeRateQuote | None = (
        None
        if currency_code == CARRIER_CURRENCY
        else exchange_rate_registry.find_rate(CARRIER_CURRENCY, currency_code)
    )
    return price_rental(
        monthly_cost,
        settings.price_markup_percent,
        currency_code,
        None if rate is None else rate.rate_value,
    )
