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
    def try_acquire(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        now: Microseconds,
    ) -> bool:
        """
        Count one request for `key` (a technical key, e.g. "widget-poll:ip:…")
        and tell whether it stays within `limit` requests per sliding window
        of `window_seconds` in this process. A refused request is not counted.
        """
        raise NotImplementedError
