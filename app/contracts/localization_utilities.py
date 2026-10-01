"""Deterministic localization helpers shared by many slices."""

from typing import Protocol

from app.contracts.utility_contract import UtilityContract
from app.schemas.dto.localization import LocalizedText, PhoneNumberDetails
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import (
    LocalizedTextValue,
    RawPhoneNumberInput,
)


class PhoneNumberParserContract(UtilityContract, Protocol):
    def parse(
        self,
        raw_phone_number: RawPhoneNumberInput,
        country_hint: CountryCode | None,
    ) -> PhoneNumberDetails:
        """
        Parse a number typed in any national or international format.

        `country_hint` is required only for national formats without "+".

        Raises:
            InvalidPhoneNumberError: not a valid number of any country.
        """
        raise NotImplementedError


class LocalizedTextResolverContract(UtilityContract, Protocol):
    def resolve(
        self,
        text: LocalizedText,
        language_tag: LanguageTag,
    ) -> LocalizedTextValue:
        """Pick the best value: exact tag, base language, English, any."""
        raise NotImplementedError


class LanguageDetectorContract(UtilityContract, Protocol):
    def detect(
        self,
        text: str,
        candidate_languages: list[LanguageTag],
        fallback_language: LanguageTag,
    ) -> LanguageTag:
        """Pick the candidate language the text is most likely written in."""
        raise NotImplementedError
