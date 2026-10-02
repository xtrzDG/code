"""Read-only catalogs (countries, languages, niches, plans) and process locks."""

from contextlib import AbstractContextManager
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.registry_contract import RegistryContract
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.localization import CountryProfile, LanguageProfile
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
)


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
        Lock serializing the check-and-reserve step of login code sends in
        this process, so parallel requests cannot all pass the limits.
        """
        raise NotImplementedError


class RequestRateLimitRegistryContract(RegistryContract, Protocol):
    def try_acquire_all(
        self,
        counters: list[tuple[str, int]],
        window_seconds: int,
        now: Microseconds,
    ) -> str | None:
        """
        Count one request for every `(key, limit)` only when all of them stay
        within their limits, in one step; otherwise count none and return
        the first key whose limit is used up. A refused request leaves no
        state behind (no counter is created for its keys).
        """
        raise NotImplementedError

    def seconds_until_free(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        now: Microseconds,
    ) -> int:
        """
        Whole seconds until `key` may make a request again under `limit`
        per `window_seconds` (0 when it may now): the Retry-After of a
        refused request.
        """
        raise NotImplementedError
