"""Read-only catalogs (countries, languages, niches, plans), locks and rate limits
shared by every process."""

from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.registry_contract import RegistryContract
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.localization import CountryProfile, LanguageProfile
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RetryAfterSeconds,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.schemas.typings.storage.constrained_integers import DocumentCount


class CountryRegistryContract(RegistryContract, Protocol):
    def get(self, country_code: CountryCode) -> CountryProfile:
        """Raises UnknownCountryError for codes outside ISO 3166-1."""
        raise NotImplementedError

    def list_all(self) -> list[CountryProfile]:
        """Every country with a phone numbering plan, ordered by code."""
        raise NotImplementedError


class LanguageRegistryContract(RegistryContract, Protocol):
    def get(self, language_tag: LanguageTag) -> LanguageProfile:
        """Raises UnsupportedLanguageError for tags unknown to CLDR."""
        raise NotImplementedError

    def list_all(self) -> list[LanguageProfile]:
        raise NotImplementedError


class NicheTemplateRegistryContract(RegistryContract, Protocol):
    def get(self, niche_key: NicheKey) -> NicheTemplate:
        raise NotImplementedError

    def list_all(self) -> list[NicheTemplate]:
        raise NotImplementedError


class PlanRegistryContract(RegistryContract, Protocol):
    def get(self, plan_key: PlanKey) -> PlanDefinition:
        raise NotImplementedError

    def list_all(self) -> list[PlanDefinition]:
        raise NotImplementedError

    def find_local_monthly_price(
        self,
        plan_key: PlanKey,
        currency_code: CurrencyCode,
    ) -> Money | None:
        """Explicit price-book price in a local currency, if one is set."""
        raise NotImplementedError

    def find_local_setup_fee(
        self,
        plan_key: PlanKey,
        currency_code: CurrencyCode,
    ) -> Money | None:
        raise NotImplementedError


class LoginCodeSendLockRegistryContract(RegistryContract, Protocol):
    def lock(self) -> AbstractContextManager[object]:
        """
        Lock serializing the check-and-reserve step of login code sends
        across every process, so parallel requests cannot all pass the
        limits. The block's storage writes commit with the lock's release.
        """
        raise NotImplementedError


class CustomerMessageLockRegistryContract(RegistryContract, Protocol):
    def lock_for_customer(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
    ) -> AbstractContextManager[object]:
        """
        Lock serializing the turns of one customer in one channel across
        every process (API instances answering the widget, workers answering
        the inbox), held for a whole turn, model calls included.
        """
        raise NotImplementedError


class RequestRateLimitRegistryContract(RegistryContract, Protocol):
    """
    Sliding-window request limits of public endpoints (the website widget,
    login code checks), counted for every API instance together.
    """

    def try_acquire_all(
        self,
        counters: Sequence[RateLimitCounter],
        window: RateWindowSeconds,
        now: Microseconds,
    ) -> RateLimitKey | None:
        """
        Count one request for every counter only when all of them stay
        within their limits, in one step; otherwise count none and return
        the first key whose limit is used up. A refused request leaves no
        state behind (no counter is created for its keys).
        """
        raise NotImplementedError

    def seconds_until_free(
        self,
        counter: RateLimitCounter,
        window: RateWindowSeconds,
        now: Microseconds,
    ) -> RetryAfterSeconds:
        """
        Whole seconds until the counter allows one more request (the
        Retry-After of a refused request, at least 1).
        """
        raise NotImplementedError

    def forget_expired(self, now: Microseconds) -> DocumentCount:
        """Drop counters no limit needs any more; how many went."""
        raise NotImplementedError
