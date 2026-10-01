"""Fakes of foundation contracts implemented by other slices.

The real phone parser and text resolver come from the localization slice;
these fakes follow the same contracts closely enough for this slice's tests.
"""

import phonenumbers

from app.contracts.localization_utilities import (
    LocalizedTextResolverContract,
    PhoneNumberParserContract,
)
from app.contracts.operator_contract import OperatorContract
from app.schemas.constants.localization import PhoneNumberKind
from app.schemas.dto.localization import LocalizedText, PhoneNumberDetails
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    InvalidPhoneNumberError,
)
from app.schemas.typings.localization.constrained_integers import CountryCallingCode
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import (
    FormattedPhoneNumber,
    LocalizedTextValue,
    RawPhoneNumberInput,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken


class FakePhoneNumberParser(PhoneNumberParserContract):
    """Parses numbers of any country with the phonenumbers library."""

    def __init__(self) -> None:
        self.country_hints: list[CountryCode | None] = []

    def parse(
        self,
        raw_phone_number: RawPhoneNumberInput,
        country_hint: CountryCode | None,
    ) -> PhoneNumberDetails:
        self.country_hints.append(country_hint)
        try:
            parsed = phonenumbers.parse(raw_phone_number, country_hint)
        except phonenumbers.NumberParseException as error:
            raise InvalidPhoneNumberError(
                f"{raw_phone_number!r} is not a phone number."
            ) from error

        if not phonenumbers.is_valid_number(parsed):
            raise InvalidPhoneNumberError(f"{raw_phone_number!r} is not valid.")

        region: str | None = phonenumbers.region_code_for_number(parsed)
        is_mobile: bool = (
            phonenumbers.number_type(parsed) == phonenumbers.PhoneNumberType.MOBILE
        )
        return PhoneNumberDetails(
            e164=E164PhoneNumber(
                phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            ),
            country_code=CountryCode(region or "ZZ"),
            calling_code=CountryCallingCode(parsed.country_code or 1),
            kind=PhoneNumberKind.MOBILE if is_mobile else PhoneNumberKind.OTHER,
            is_mobile=is_mobile,
            international_format=FormattedPhoneNumber(
                phonenumbers.format_number(
                    parsed,
                    phonenumbers.PhoneNumberFormat.INTERNATIONAL,
                )
            ),
            national_format=FormattedPhoneNumber(
                phonenumbers.format_number(
                    parsed,
                    phonenumbers.PhoneNumberFormat.NATIONAL,
                )
            ),
            timezones=[TimezoneName("UTC")],
        )


class FakeLocalizedTextResolver(LocalizedTextResolverContract):
    """Requested tag, then its base language, then English, then any value."""

    def resolve(
        self,
        text: LocalizedText,
        language_tag: LanguageTag,
    ) -> LocalizedTextValue:
        base_language: str = language_tag.split("-")[0]
        for candidate in (language_tag, base_language, "en"):
            for value_language, value in text.values.items():
                if value_language == candidate:
                    return value

        return next(iter(text.values.values()))


class FakeUserAuthenticationOperator(OperatorContract[AccessToken, UserId]):
    """Maps known bearer tokens to users."""

    def __init__(self, users_by_token: dict[str, UserId]) -> None:
        self._users_by_token: dict[str, UserId] = users_by_token

    def operate(self, input_data: AccessToken) -> UserId:
        user_id: UserId | None = self._users_by_token.get(input_data)
        if user_id is None:
            raise AuthenticationRequiredError("Unknown access token.")

        return user_id
