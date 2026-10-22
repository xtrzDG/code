"""
The carrier behind rented numbers: Twilio prices a kind before its numbers
are offered, a rented number is imported into ElevenLabs as a Twilio
number, giving it back removes it from ElevenLabs before Twilio, and a
server without the settings names what is missing.
"""

import pytest

from app.adapters.telephony.twilio_phone_number_provisioner_adapter import (
    TwilioPhoneNumberProvisionerAdapter,
)
from app.adapters.telephony.unconfigured_phone_number_provisioner_adapter import (
    UnconfiguredPhoneNumberProvisionerAdapter,
)
from app.containers.phone_number_factories import build_phone_number_provisioner
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.configurations.phone_number_settings import PhoneNumberSettings
from app.schemas.constants.phone_numbers import PhoneNumberProvider, PhoneNumberType
from app.schemas.dto.phone_numbers.provisioning import (
    PhoneNumberPurchase,
    PhoneNumberRelease,
    PhoneNumberSearchQuery,
    VoicePlatformImport,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.schemas.typings.messaging.constrained_strings import TwilioAccountSid
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.telephony.constrained_integers import (
    PhoneNumberOfferCount,
    PhoneNumberPriceMarkupPercent,
)
from app.schemas.typings.telephony.constrained_strings import PhoneNumberLabel
from app.schemas.typings.telephony.strings import (
    ProviderPhoneNumberId,
    VoicePlatformPhoneNumberId,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.phone_numbers.provisioner_fakes import (
    FakeElevenLabsNumbersClient,
    FakeTwilioNumbersClient,
)

ACCOUNT = TwilioAccountSid("AC" + "0" * 32)
# The Twilio account of login codes, which rents the numbers too.
SMS_LOGIN: dict[str, str] = {
    "TWILIO_ACCOUNT_SID": str(ACCOUNT),
    "TWILIO_AUTH_TOKEN": "test-token-0000",
    "TWILIO_FROM_NUMBER": "+15005550006",
}
QUERY = PhoneNumberSearchQuery(
    country_code=CountryCode("US"),
    number_type=PhoneNumberType.LOCAL,
    limit=PhoneNumberOfferCount(2),
)


def adapter(
    twilio: FakeTwilioNumbersClient, elevenlabs: FakeElevenLabsNumbersClient
) -> TwilioPhoneNumberProvisionerAdapter:
    return TwilioPhoneNumberProvisionerAdapter(
        twilio, elevenlabs, ACCOUNT, PlatformSecret("test-token-0000")
    )


def test_a_search_offers_numbers_of_a_priced_kind_up_to_the_limit() -> None:
    twilio = FakeTwilioNumbersClient()

    result = adapter(twilio, FakeElevenLabsNumbersClient()).search_numbers(QUERY)

    assert int(result.monthly_cost_micro_usd or 0) == 1_150_000
    assert [str(number.phone_number) for number in result.numbers] == [
        "+15125550142",
        "+15125550187",
    ]
    assert twilio.calls == ["price US local", "search US local"]


def test_a_kind_twilio_does_not_price_offers_nothing_and_asks_no_further() -> None:
    twilio = FakeTwilioNumbersClient(price=None)

    result = adapter(twilio, FakeElevenLabsNumbersClient()).search_numbers(QUERY)

    assert result.numbers == []
    assert result.monthly_cost_micro_usd is None
    assert twilio.calls == ["price US local"]


def test_renting_imports_and_releasing_removes_from_elevenlabs_first() -> None:
    twilio = FakeTwilioNumbersClient()
    elevenlabs = FakeElevenLabsNumbersClient()
    provisioner = adapter(twilio, elevenlabs)

    rented = provisioner.buy_number(
        PhoneNumberPurchase(
            phone_number=E164PhoneNumber("+15125550142"),
            label=PhoneNumberLabel("Austin Coffee Lab"),
        )
    )
    voice_id = provisioner.import_number(
        VoicePlatformImport(
            phone_number=rented.phone_number,
            label=PhoneNumberLabel("Austin Coffee Lab"),
            agent_id=VoiceAgentId("agent_7"),
        )
    )
    provisioner.assign_agent(voice_id, None)
    provisioner.release_number(
        PhoneNumberRelease(
            provider_number_id=rented.provider_number_id,
            voice_platform_number_id=voice_id,
        )
    )

    assert rented.provider is PhoneNumberProvider.TWILIO
    assert elevenlabs.calls == [
        f"import +15125550142 {ACCOUNT} agent_7",
        "assign phnum_0042 None",
        "delete phnum_0042",
    ]
    assert twilio.calls[-1] == f"release {rented.provider_number_id}"
    assert provisioner.list_missing_settings() == []


def test_a_number_never_imported_goes_straight_back_to_twilio() -> None:
    twilio = FakeTwilioNumbersClient()
    elevenlabs = FakeElevenLabsNumbersClient()

    adapter(twilio, elevenlabs).release_number(
        PhoneNumberRelease(provider_number_id=ProviderPhoneNumberId("PN1"))
    )

    assert elevenlabs.calls == []
    assert twilio.calls == ["release PN1"]


def test_the_stand_in_names_what_is_missing_and_reaches_no_carrier() -> None:
    missing = [EnvironmentVariableName("TWILIO_AUTH_TOKEN")]
    stand_in = UnconfiguredPhoneNumberProvisionerAdapter(missing)

    assert stand_in.list_missing_settings() == missing
    for call in (
        lambda: stand_in.search_numbers(QUERY),
        lambda: stand_in.release_number(
            PhoneNumberRelease(provider_number_id=ProviderPhoneNumberId("PN1"))
        ),
        lambda: stand_in.assign_agent(VoicePlatformPhoneNumberId("phnum_1"), None),
    ):
        with pytest.raises(ExternalServiceError, match="TWILIO_AUTH_TOKEN"):
            call()


def settings(**variables: str) -> AppSettings:
    return assemble_app_settings({"APP_ENV": "development", **variables})


@pytest.mark.parametrize(
    ("variables", "missing"),
    [
        ({}, ["PHONE_NUMBER_PROVIDER"]),
        (
            {"PHONE_NUMBER_PROVIDER": "twilio"},
            ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "ELEVENLABS_API_KEY"],
        ),
        (
            {"PHONE_NUMBER_PROVIDER": "Twilio", **SMS_LOGIN},
            ["ELEVENLABS_API_KEY"],
        ),
    ],
)
def test_the_settings_choose_the_stand_in_until_every_key_is_set(
    variables: dict[str, str], missing: list[str]
) -> None:
    provisioner = build_phone_number_provisioner(settings(**variables))

    assert isinstance(provisioner, UnconfiguredPhoneNumberProvisionerAdapter)
    assert [str(name) for name in provisioner.list_missing_settings()] == missing


def test_twilio_with_every_key_rents_numbers() -> None:
    configured = settings(
        PHONE_NUMBER_PROVIDER="twilio",
        ELEVENLABS_API_KEY="test-key-0000",
        **SMS_LOGIN,
        PHONE_NUMBER_PRICE_MARKUP_PERCENT="45",
    )

    assert isinstance(
        build_phone_number_provisioner(configured), TwilioPhoneNumberProvisionerAdapter
    )
    assert configured.phone_numbers == PhoneNumberSettings(
        provider=PhoneNumberProvider.TWILIO,
        price_markup_percent=PhoneNumberPriceMarkupPercent(45),
    )


def test_the_default_markup_is_thirty_percent_and_a_bad_one_is_refused() -> None:
    assert int(settings().phone_numbers.price_markup_percent) == 30
    with pytest.raises(ValidationFailedError, match="PHONE_NUMBER_PRICE_MARKUP"):
        settings(PHONE_NUMBER_PRICE_MARKUP_PERCENT="900")
    with pytest.raises(ValidationFailedError, match="PHONE_NUMBER_PROVIDER"):
        settings(PHONE_NUMBER_PROVIDER="carrier-pigeon")
