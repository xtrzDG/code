from hashlib import sha256

import pytest

from app.schemas.constants.localization import PhoneNumberKind
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.strings import RawManagerContactAddress
from app.schemas.typings.localization.constrained_integers import CountryCallingCode
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.schemas.typings.localization.strings import (
    FormattedPhoneNumber,
    RawPhoneNumberInput,
)
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from app.schemas.typings.users.strings import AccessToken, RawEmailAddressInput
from app.utilities.security.access_tokens import (
    generate_access_token,
    hash_access_token,
)
from app.utilities.security.email_addresses import parse_email_address
from app.utilities.security.login_destination_masking import (
    mask_e164_phone_number,
    mask_email_address,
    mask_phone_number,
)
from app.utilities.security.one_time_codes import (
    generate_otp_code,
    hash_otp_code,
    is_otp_code_matching,
)
from tests.users.accounts_phones import PhonenumbersParser


def test_generated_codes_are_six_random_digits() -> None:
    codes = {generate_otp_code() for _ in range(200)}

    assert all(len(code) == 6 and code.isdigit() for code in codes)
    assert len(codes) > 150


def test_code_hash_is_keyed_by_the_challenge() -> None:
    first_challenge, second_challenge = OtpChallengeId(), OtpChallengeId()
    code = OtpCode("042317")

    first_hash = hash_otp_code(first_challenge, code)

    assert first_hash == hash_otp_code(first_challenge, code)
    assert first_hash != hash_otp_code(second_challenge, code)
    assert first_hash != sha256(b"042317").hexdigest()
    assert "042317" not in first_hash
    assert len(first_hash) == 64
    assert is_otp_code_matching(first_challenge, code, first_hash) is True
    assert is_otp_code_matching(first_challenge, OtpCode("042318"), first_hash) is False
    assert is_otp_code_matching(second_challenge, code, first_hash) is False


def test_access_tokens_are_random_and_stored_as_sha256() -> None:
    tokens = {generate_access_token() for _ in range(50)}

    assert len(tokens) == 50
    token = AccessToken("example-token")
    assert hash_access_token(token) == sha256(b"example-token").hexdigest()


@pytest.mark.parametrize(
    ("raw_phone_number", "expected_mask"),
    [
        ("+995 555 12 34 56", "+995 *** ** ** 56"),
        ("+1 201-555-0123", "+1 ***-***-**23"),
        ("+972 50-234-5678", "+972 **-***-**78"),
        ("+971 50 123 4567", "+971 ** *** **67"),
        ("+81 90-1234-5678", "+81 **-****-**78"),
    ],
)
def test_phone_masks_keep_calling_code_grouping_and_last_two_digits(
    raw_phone_number: str,
    expected_mask: str,
) -> None:
    details = PhonenumbersParser().parse(RawPhoneNumberInput(raw_phone_number), None)

    assert mask_phone_number(details) == expected_mask


def test_phone_mask_falls_back_when_the_format_is_unexpected() -> None:
    details = PhoneNumberDetails(
        e164=E164PhoneNumber("+995555123456"),
        country_code=CountryCode("GE"),
        calling_code=CountryCallingCode(995),
        kind=PhoneNumberKind.MOBILE,
        is_mobile=True,
        international_format=FormattedPhoneNumber("555 12 34 56"),
        national_format=FormattedPhoneNumber("555 12 34 56"),
    )

    assert mask_phone_number(details) == "+**********56"
    assert mask_e164_phone_number(E164PhoneNumber("+12015550123")) == "+*********23"


@pytest.mark.parametrize(
    ("email", "expected_mask"),
    [
        ("owner@example.com", "o***r@example.com"),
        ("ab@example.com", "a***@example.com"),
        ("a@example.com", "a***@example.com"),
    ],
)
def test_email_masks_keep_the_domain(email: str, expected_mask: str) -> None:
    assert mask_email_address(EmailAddress(email)) == expected_mask


@pytest.mark.parametrize(
    ("raw_email", "expected_email"),
    [
        (" Owner@Example.COM ", "owner@example.com"),
        ("first.last+tag@sub.example.co.uk", "first.last+tag@sub.example.co.uk"),
        ("owner@пример.рф", "owner@xn--e1afmkfd.xn--p1ai"),
        ("owner@bücher.de", "owner@xn--bcher-kva.de"),
    ],
)
def test_email_addresses_are_normalized(raw_email: str, expected_email: str) -> None:
    assert parse_email_address(RawEmailAddressInput(raw_email)) == expected_email
    assert parse_email_address(RawManagerContactAddress(raw_email)) == expected_email


@pytest.mark.parametrize(
    "raw_email",
    ["", "owner", "owner@", "@example.com", "owner@example", "ow ner@example.com"],
)
def test_invalid_email_addresses_are_rejected(raw_email: str) -> None:
    with pytest.raises(ValidationFailedError):
        parse_email_address(RawEmailAddressInput(raw_email))
