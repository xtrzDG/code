"""
A text-back SMS goes only where a missed call's caller id cannot be turned
into SMS pumping: never to premium, satellite, landline or toll-free
numbers, only to the business's own country and the EU, never to a
restricted country (the destination rules of the login codes). WhatsApp
still carries a text-back to any number; when WhatsApp refuses it, no
SMS follows to a refused number.
"""

from typing import Any

import pytest

from app.registries.localization.country_registry import CountryRegistry
from app.registries.localization.high_cost_phone_number_registry import (
    HighCostPhoneNumberRegistry,
)
from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackChannel,
    TextBackSkipReason,
    TextBackStatus,
)
from app.schemas.constants.localization import DataRegion
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
    PhoneNumberPrefix,
)
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.use_cases.voice.missed_calls.text_back_destinations import (
    TextBackSmsDestinations,
)
from app.use_cases.voice.missed_calls.text_back_messages import TextBackSms
from app.utilities.calls.call_follow_up_keys import missed_call_id_of
from app.utilities.calls.text_back_jobs import (
    SEND_TEXT_BACK_JOB,
    encode_text_back_payload,
)
from tests.calls.call_steps import (
    connect_whatsapp,
    missed_calls,
    report_missed_call,
    save_call_settings,
    whatsapp_templates,
)
from tests.channels.voice_setup import CALLER, VoiceSetup, build_voice_setup

GEORGIAN_LANDLINE: str = "+995322123456"
GEORGIAN_TOLL_FREE: str = "+995800123456"
ITALIAN_MOBILE: str = "+393471234567"
CYPRIOT_MOBILE: str = "+35799123456"
US_NUMBER: str = "+12015550123"
UK_PREMIUM: str = "+449098765432"
SATELLITE: str = "+881631234567"
TEMPLATE_MISSING: dict[str, Any] = {
    "error": {"code": 132001, "message": "(#132001) Template name does not exist"}
}


@pytest.fixture
def setup() -> VoiceSetup:
    voice_setup = build_voice_setup()
    save_call_settings(voice_setup, template_name=None)
    return voice_setup


def destinations(
    setup: VoiceSetup,
    restricted: list[CountryCode] | None = None,
    denied: list[PhoneNumberPrefix] | None = None,
) -> TextBackSmsDestinations:
    return TextBackSmsDestinations(
        HighCostPhoneNumberRegistry(denied or []),
        CountryRegistry(
            setup.testbed.language_registry,
            setup.testbed.wall_clock,
            DataRegion.EU,
            restricted or [],
        ),
        setup.testbed.phone_number_parser,
    )


def only_missed_call(setup: VoiceSetup) -> MissedCallDocument:
    [missed] = missed_calls(setup)
    return missed


class TestTheRule:
    @pytest.mark.parametrize(
        "number", [CALLER, ITALIAN_MOBILE, CYPRIOT_MOBILE, "+4915112345678"]
    )
    def test_mobiles_of_the_country_and_the_eu_get_one(
        self, setup: VoiceSetup, number: str
    ) -> None:
        assert destinations(setup).allows(setup.business, E164PhoneNumber(number))

    @pytest.mark.parametrize(
        "number",
        [
            GEORGIAN_LANDLINE,
            GEORGIAN_TOLL_FREE,
            UK_PREMIUM,
            SATELLITE,
            US_NUMBER,
            "+79161234567",
        ],
    )
    def test_risky_and_unreachable_numbers_never_do(
        self, setup: VoiceSetup, number: str
    ) -> None:
        assert not destinations(setup).allows(setup.business, E164PhoneNumber(number))

    def test_restricted_countries_and_denied_ranges_never_do(
        self, setup: VoiceSetup
    ) -> None:
        restricted = destinations(setup, restricted=[CountryCode("CY")])
        denied = destinations(setup, denied=[PhoneNumberPrefix("+99559912")])

        assert not restricted.allows(setup.business, E164PhoneNumber(CYPRIOT_MOBILE))
        assert not denied.allows(setup.business, E164PhoneNumber(CALLER))
        assert denied.allows(setup.business, E164PhoneNumber("+995599765432"))

    def test_an_unparsable_number_never_does(self, setup: VoiceSetup) -> None:
        assert not destinations(setup).allows(
            setup.business, E164PhoneNumber("+9951234567")
        )

    def test_the_sender_refuses_such_a_number_itself(self, setup: VoiceSetup) -> None:
        report_missed_call(setup, caller=SATELLITE)
        sms = TextBackSms(
            setup.testbed.sms_client, setup.testbed.text_resolver, destinations(setup)
        )

        with pytest.raises(ValidationFailedError):
            sms.send(
                setup.business, only_missed_call(setup), E164PhoneNumber(SATELLITE)
            )
        assert setup.testbed.sms_client.sent == []


class TestMissedCalls:
    @pytest.mark.parametrize("caller", [UK_PREMIUM, US_NUMBER, GEORGIAN_LANDLINE])
    def test_a_spoofed_caller_id_gets_no_sms(
        self, setup: VoiceSetup, caller: str
    ) -> None:
        report_missed_call(setup, caller=caller)
        setup.testbed.run_worker()

        missed = only_missed_call(setup)
        assert missed.status is TextBackStatus.SKIPPED
        assert missed.skip_reason is TextBackSkipReason.NO_CHANNEL
        assert setup.testbed.sms_client.sent == []

    def test_an_eu_mobile_gets_its_sms(self, setup: VoiceSetup) -> None:
        report_missed_call(setup, caller=ITALIAN_MOBILE)
        setup.testbed.run_worker()

        assert only_missed_call(setup).status is TextBackStatus.SENT
        [(recipient, _)] = setup.testbed.sms_client.sent
        assert recipient == ITALIAN_MOBILE

    def test_whatsapp_still_reaches_a_foreign_caller(self, setup: VoiceSetup) -> None:
        save_call_settings(setup)
        connect_whatsapp(setup)
        report_missed_call(setup, caller=US_NUMBER)
        setup.testbed.run_worker()

        missed = only_missed_call(setup)
        assert missed.status is TextBackStatus.SENT
        assert missed.channel is TextBackChannel.WHATSAPP
        assert len(whatsapp_templates(setup)) == 1

    def test_no_sms_follows_a_refused_template_to_a_foreign_caller(
        self, setup: VoiceSetup
    ) -> None:
        save_call_settings(setup)
        connect_whatsapp(setup)
        setup.testbed.meta_transport.respond(
            "POST", r"/messages$", TEMPLATE_MISSING, status_code=404
        )
        report_missed_call(setup, caller=US_NUMBER)
        setup.testbed.run_worker()

        missed = only_missed_call(setup)
        assert missed.status is TextBackStatus.FAILED
        assert missed.channel is TextBackChannel.WHATSAPP
        assert setup.testbed.sms_client.sent == []

    def test_an_sms_queued_before_the_rule_is_not_sent(self, setup: VoiceSetup) -> None:
        now = setup.testbed.clock.now_microseconds()
        missed = MissedCallDocument(
            id=missed_call_id_of(
                setup.business.id, MissedCallSource.PBX, ProviderCallId("in_old")
            ),
            business_id=setup.business.id,
            source=MissedCallSource.PBX,
            provider_call_id=ProviderCallId("in_old"),
            reason=MissedCallReason.BUSY,
            caller_phone_number=E164PhoneNumber(SATELLITE),
            called_at=now,
            language=LanguageTag("ka"),
            status=TextBackStatus.QUEUED,
            channel=TextBackChannel.SMS,
            created_at=now,
            updated_at=now,
        )
        setup.testbed.missed_call_repo.insert_if_new(missed)

        setup.testbed.send_text_back.run(
            QueuedJobInput(
                job_id=QueuedJobId(),
                job_name=SEND_TEXT_BACK_JOB,
                payload=encode_text_back_payload(missed.id),
                business_id=setup.business.id,
            )
        )

        stored = only_missed_call(setup)
        assert stored.status is TextBackStatus.SKIPPED
        assert stored.skip_reason is TextBackSkipReason.NO_CHANNEL
        assert setup.testbed.sms_client.sent == []
