"""
The call fallback of a rented number: once the voice platform has the
number, the carrier sends calls it cannot take to the business's address
on the platform (which puts them through to the staff mobile); the
maintenance job keeps it so.
"""

import pytest

from app.adapters.telephony.twilio_phone_number_provisioner_adapter import (
    TwilioPhoneNumberProvisionerAdapter,
)
from app.adapters.telephony.unconfigured_phone_number_provisioner_adapter import (
    UnconfiguredPhoneNumberProvisionerAdapter,
)
from app.containers.phone_number_factories import build_phone_number_provisioner
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.phone_numbers import PhoneNumberReleaseReason
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.messaging.constrained_strings import TwilioAccountSid
from app.schemas.typings.platform.constrained_strings import (
    EnvironmentVariableName,
    JobName,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.telephony.constrained_strings import VoiceFallbackUrl
from app.schemas.typings.telephony.strings import ProviderPhoneNumberId
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.telephony.number_release import mark_releasing
from tests.phone_numbers.phone_world import PhoneWorld
from tests.phone_numbers.provisioner_fakes import (
    FakeElevenLabsNumbersClient,
    FakeTwilioNumbersClient,
)
from tests.resilience.test_circuit_breaker import Ticks

BASE: str = "https://api.workshop.test"
MOVED_BASE: str = "https://api2.workshop.test"
BUSINESS_ID = BusinessId("business_fd43b272-3035-4a74-a29f-96b1631dd8b5")
ACCOUNT = TwilioAccountSid("AC" + "0" * 32)
TOKEN = PlatformSecret("test-token-0000")
TWILIO_KEYS: dict[str, str] = {
    "PHONE_NUMBER_PROVIDER": "twilio",
    "ELEVENLABS_API_KEY": "test-key-0000",
    "TWILIO_ACCOUNT_SID": str(ACCOUNT),
    "TWILIO_AUTH_TOKEN": str(TOKEN),
    "TWILIO_FROM_NUMBER": "+15005550006",
}


def settings(**variables: str) -> AppSettings:
    return assemble_app_settings({"APP_ENV": "development", **variables})


def fallback_of(base: str, business: BusinessDocument | BusinessId) -> str:
    business_id = business.id if isinstance(business, BusinessDocument) else business
    return f"{base}/v1/telephony/twilio/voice-fallback/{business_id}"


def maintain(world: PhoneWorld) -> int:
    report = world.maintain.run(
        JobTick(
            job_name=JobName("maintain_phone_numbers"),
            scheduled_at=world.clock.now(),
        )
    )
    return int(report.processed_count)


def fallback_world() -> PhoneWorld:
    world = PhoneWorld()
    world.provisioner.voice_fallback_base = BASE
    return world


def test_a_rented_number_falls_back_to_its_business_at_once() -> None:
    world = fallback_world()
    owner, business = world.owner_and_business()

    world.rent_austin_number(owner, business)

    number = world.rented(business)
    assert str(number.voice_fallback_url) == fallback_of(BASE, business)
    assert {sid: str(url) for sid, url in world.provisioner.fallbacks.items()} == {
        str(number.provider_number_id): fallback_of(BASE, business)
    }
    assert maintain(world) == 0


def test_the_fallback_waits_for_the_import_and_a_refusal_for_the_next_run() -> None:
    world = fallback_world()
    world.provisioner.is_import_failing = True
    owner, business = world.owner_and_business()
    world.rent_austin_number(owner, business)

    # Not imported: the carrier's voice webhook is not the platform's yet.
    assert world.provisioner.fallbacks == {}
    assert world.rented(business).voice_fallback_url is None

    world.provisioner.is_import_failing = False
    world.provisioner.is_fallback_failing = True
    assert maintain(world) == 1
    number = world.rented(business)
    assert number.voice_platform_number_id is not None
    assert number.voice_fallback_url is None

    world.provisioner.is_fallback_failing = False
    assert maintain(world) == 1
    assert str(world.rented(business).voice_fallback_url) == fallback_of(BASE, business)
    assert maintain(world) == 0


def test_a_moved_address_is_set_again() -> None:
    world = fallback_world()
    owner, business = world.owner_and_business()
    world.rent_austin_number(owner, business)

    world.provisioner.voice_fallback_base = MOVED_BASE

    assert maintain(world) == 1
    number = world.rented(business)
    assert str(number.voice_fallback_url) == fallback_of(MOVED_BASE, business)
    assert str(world.provisioner.fallbacks[str(number.provider_number_id)]) == (
        fallback_of(MOVED_BASE, business)
    )
    assert maintain(world) == 0


def test_a_number_being_given_back_gets_no_fallback() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    world.rent_austin_number(owner, business)
    number = world.rented(business)
    world.phone_number_repo.modify(
        business.id,
        number.id,
        lambda stored: mark_releasing(
            stored, PhoneNumberReleaseReason.OWNER, world.clock.now()
        ),
    )
    world.provisioner.voice_fallback_base = BASE
    world.provisioner.is_release_failing = True

    assert maintain(world) == 0
    assert world.provisioner.fallbacks == {}


def test_twilio_points_the_number_at_the_business_s_address() -> None:
    twilio = FakeTwilioNumbersClient()
    provisioner = TwilioPhoneNumberProvisionerAdapter(
        twilio,
        FakeElevenLabsNumbersClient(),
        ACCOUNT,
        TOKEN,
        public_base_url=PublicBaseUrl(BASE + "/"),
    )
    url = provisioner.voice_fallback_url_of(BUSINESS_ID)
    assert url is not None

    provisioner.route_voice_fallback(ProviderPhoneNumberId("PN1"), url)

    assert str(url) == fallback_of(BASE, BUSINESS_ID)
    assert twilio.calls == [f"fallback PN1 {fallback_of(BASE, BUSINESS_ID)}"]


def test_the_fallback_address_comes_from_app_base_url() -> None:
    breaker = CircuitBreakerFacilitator(Ticks().clock())
    configured = build_phone_number_provisioner(
        settings(APP_BASE_URL=BASE, **TWILIO_KEYS), breaker
    )
    without_address = build_phone_number_provisioner(settings(**TWILIO_KEYS), breaker)
    stand_in = UnconfiguredPhoneNumberProvisionerAdapter(
        [EnvironmentVariableName("PHONE_NUMBER_PROVIDER")]
    )

    assert str(configured.voice_fallback_url_of(BUSINESS_ID)) == fallback_of(
        BASE, BUSINESS_ID
    )
    assert without_address.voice_fallback_url_of(BUSINESS_ID) is None
    assert stand_in.voice_fallback_url_of(BUSINESS_ID) is None
    with pytest.raises(ExternalServiceError, match="PHONE_NUMBER_PROVIDER"):
        stand_in.route_voice_fallback(
            ProviderPhoneNumberId("PN1"),
            VoiceFallbackUrl(fallback_of(BASE, BUSINESS_ID)),
        )
