"""
The call fallback of a rented line: when the voice platform cannot take a
call, Twilio asks the business's address on the platform, which puts the
caller through to the staff mobile on duty and tells the owner (once an
hour); with nobody to take the call, or a mobile that does not answer,
the caller is a missed call with its text-back.
"""

from collections.abc import Callable

import pytest

from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackStatus,
)
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.calls.call_fallback_steps import (
    CALL_SID,
    STAFF_MOBILE,
    dial_form,
    dial_path,
    fallback_form,
    fallback_path,
    fallback_settings,
    post_twilio,
    set_staff_mobile,
    sign_twilio,
)
from tests.calls.call_steps import (
    add_staff_chat,
    connect_whatsapp,
    missed_calls,
    save_call_settings,
    staff_texts,
    whatsapp_templates,
)
from tests.channels.channels_payloads import HttpResponse
from tests.channels.voice_setup import CALLER, VoiceSetup, build_voice_setup

HANGUP: str = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
GONE = BusinessId("business_fd43b272-3035-4a74-a29f-96b1631dd8b5")
NOTICE_TITLE: str = "The phone assistant could not take a call · Funicular VR"


def dial_twiml(business_id: BusinessId, number: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?><Response>'
        '<Dial timeout="20" answerOnBridge="true" action="https://api.workshop.test'
        f'{dial_path(business_id)}" method="POST">'
        f"<Number>{number}</Number></Dial></Response>"
    )


def notices(setup: VoiceSetup) -> list[str]:
    """The owner's notices of the fallback, as the staff chat got them."""

    return [
        str(text.text)
        for text in staff_texts(setup)
        if str(text.text).startswith(NOTICE_TITLE)
    ]


def call_falls_back(setup: VoiceSetup, **form: str) -> HttpResponse:
    return post_twilio(setup, fallback_path(setup.business.id), fallback_form(**form))


def dial_ends(setup: VoiceSetup, status: str) -> HttpResponse:
    return post_twilio(setup, dial_path(setup.business.id), dial_form(status))


@pytest.fixture
def setup() -> VoiceSetup:
    voice_setup = build_voice_setup(settings=fallback_settings())
    save_call_settings(voice_setup)
    connect_whatsapp(voice_setup)
    add_staff_chat(voice_setup, language="en")
    return voice_setup


class TestPutThrough:
    def test_a_call_the_assistant_could_not_take_rings_the_staff_mobile(
        self, setup: VoiceSetup
    ) -> None:
        set_staff_mobile(setup)

        response = call_falls_back(setup)

        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("text/xml")
        assert response.text == dial_twiml(setup.business.id, STAFF_MOBILE)
        assert missed_calls(setup) == []
        [notice] = notices(setup)
        assert "put through to +995 555 12 34 56" in notice
        assert CALLER not in notice

    def test_a_manager_reachable_by_phone_is_rung_without_a_profile_phone(
        self, setup: VoiceSetup
    ) -> None:
        add_staff_chat(
            setup, channel=ManagerContactChannel.SMS, address="+995577000111"
        )

        response = call_falls_back(setup)

        assert response.text == dial_twiml(setup.business.id, "+995577000111")

    def test_the_owner_hears_of_it_once_an_hour(self, setup: VoiceSetup) -> None:
        set_staff_mobile(setup)

        for number in range(3):
            call_falls_back(setup, call_sid=f"CA{number}")
        quiet_hour = notices(setup)
        setup.testbed.clock.advance(3600)
        call_falls_back(setup, call_sid="CA9")

        assert len(quiet_hour) == 1
        assert len(notices(setup)) == 2

    def test_a_mobile_that_took_the_call_ends_it_quietly(
        self, setup: VoiceSetup
    ) -> None:
        set_staff_mobile(setup)

        response = dial_ends(setup, "completed")

        assert response.status_code == 200, response.text
        assert response.text == HANGUP
        assert missed_calls(setup) == []

    @pytest.mark.parametrize(
        ("status", "reason"),
        [
            ("no-answer", MissedCallReason.NO_ANSWER),
            ("busy", MissedCallReason.BUSY),
            ("failed", MissedCallReason.LINE_FAILED),
            ("canceled", MissedCallReason.ABANDONED),
        ],
    )
    def test_a_mobile_nobody_answered_leaves_a_missed_call(
        self, setup: VoiceSetup, status: str, reason: MissedCallReason
    ) -> None:
        set_staff_mobile(setup)

        response = dial_ends(setup, status)

        assert response.text == HANGUP
        [missed] = missed_calls(setup)
        assert missed.source is MissedCallSource.PBX
        assert missed.reason is reason
        assert str(missed.provider_call_id) == CALL_SID
        assert str(missed.caller_phone_number) == CALLER
        assert missed.status is TextBackStatus.SENT
        assert len(whatsapp_templates(setup)) == 1

    def test_the_same_dial_report_twice_is_one_missed_call(
        self, setup: VoiceSetup
    ) -> None:
        dial_ends(setup, "no-answer")
        dial_ends(setup, "no-answer")

        assert len(missed_calls(setup)) == 1
        assert len(whatsapp_templates(setup)) == 1


class TestNobodyToPutThrough:
    def test_without_a_staff_phone_the_call_is_a_missed_call(
        self, setup: VoiceSetup
    ) -> None:
        response = call_falls_back(setup)

        assert response.text == HANGUP
        [missed] = missed_calls(setup)
        assert missed.reason is MissedCallReason.NOT_STARTED
        assert missed.source is MissedCallSource.PBX
        assert missed.status is TextBackStatus.SENT
        [notice] = notices(setup)
        assert "recorded as a missed call" in notice

    @pytest.mark.parametrize(
        ("caller", "forwarded_from"),
        [(STAFF_MOBILE, None), (CALLER, "555 12 34 56")],
    )
    def test_a_call_from_the_staff_mobile_never_rings_it_again(
        self, setup: VoiceSetup, caller: str, forwarded_from: str | None
    ) -> None:
        set_staff_mobile(setup)
        form: dict[str, str] = {"caller": caller}
        if forwarded_from is not None:
            form["forwarded_from"] = forwarded_from

        response = call_falls_back(setup, **form)

        assert response.text == HANGUP
        [missed] = missed_calls(setup)
        assert missed.reason is MissedCallReason.NOT_STARTED

    def test_a_business_that_is_gone_ends_the_call(self, setup: VoiceSetup) -> None:
        set_staff_mobile(setup)

        response = post_twilio(setup, fallback_path(GONE), fallback_form())

        assert response.status_code == 200
        assert response.text == HANGUP
        assert missed_calls(setup) == []
        assert notices(setup) == []

    def test_an_address_without_a_business_is_not_found(
        self, setup: VoiceSetup
    ) -> None:
        response = post_twilio(setup, fallback_path("x"), fallback_form())

        assert response.status_code == 404


class TestTwilioSignature:
    @pytest.mark.parametrize("path_of", [fallback_path, dial_path])
    @pytest.mark.parametrize("signature", [None, "bm90IGEgc2lnbmF0dXJl"])
    def test_an_unsigned_or_forged_request_is_refused(
        self,
        setup: VoiceSetup,
        path_of: Callable[[BusinessId], str],
        signature: str | None,
    ) -> None:
        set_staff_mobile(setup)

        response = post_twilio(
            setup,
            path_of(setup.business.id),
            dial_form("no-answer"),
            signature=signature,
        )

        assert response.status_code == 401
        assert missed_calls(setup) == []
        assert notices(setup) == []

    def test_a_signature_of_another_address_is_refused(self, setup: VoiceSetup) -> None:
        fields = dial_form("no-answer")
        business_id = setup.business.id

        signed_for_the_dial = post_twilio(
            setup,
            fallback_path(business_id),
            fields,
            signature=sign_twilio(dial_path(business_id), fields),
        )
        signed_for_another_business = post_twilio(
            setup,
            dial_path(business_id),
            fields,
            signature=sign_twilio(dial_path(GONE), fields),
        )

        assert signed_for_the_dial.status_code == 401
        assert signed_for_another_business.status_code == 401
        assert missed_calls(setup) == []

    def test_a_changed_field_breaks_the_signature(self, setup: VoiceSetup) -> None:
        path = dial_path(setup.business.id)
        signed = sign_twilio(path, dial_form("completed"))

        response = post_twilio(setup, path, dial_form("no-answer"), signature=signed)

        assert response.status_code == 401
        assert missed_calls(setup) == []

    @pytest.mark.parametrize(
        "removed",
        [
            {
                "TWILIO_ACCOUNT_SID": "",
                "TWILIO_AUTH_TOKEN": "",
                "TWILIO_FROM_NUMBER": "",
            },
            {"APP_BASE_URL": ""},
        ],
    )
    def test_without_the_token_or_the_address_nothing_is_accepted(
        self, removed: dict[str, str]
    ) -> None:
        setup = build_voice_setup(settings=fallback_settings(**removed))

        response = call_falls_back(setup)

        assert response.status_code == 401

    def test_a_request_without_a_call_is_refused(self, setup: VoiceSetup) -> None:
        response = call_falls_back(setup, call_sid=" ")

        assert response.status_code == 422
        assert missed_calls(setup) == []
