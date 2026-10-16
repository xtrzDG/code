"""
Zadarma tells the platform how incoming calls to the line ended: a call
the line did not put through is a missed call, texted back and reported.
"""

import base64
import hashlib
import hmac

import pytest

from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackStatus,
)
from app.utilities.calls.zadarma_notifications import (
    is_valid_zadarma_signature,
    read_form_fields,
    read_missed_reason,
)
from tests.calls.call_steps import (
    add_staff_chat,
    connect_whatsapp,
    encode_form,
    missed_calls,
    save_call_settings,
    sign_zadarma,
    staff_texts,
    whatsapp_templates,
    zadarma_form,
)
from tests.calls.calls_http import build_calls_http_client
from tests.channels.channels_payloads import HttpResponse
from tests.channels.channels_settings import ZADARMA_API_SECRET, build_settings
from tests.channels.voice_setup import CALLER, VoiceSetup, build_voice_setup

NOTIFICATIONS: str = "/v1/telephony/zadarma/notifications"
FORM: dict[str, str] = {"Content-Type": "application/x-www-form-urlencoded"}


def notify(
    setup: VoiceSetup,
    fields: dict[str, str],
    signature: str | None = "valid",
) -> HttpResponse:
    headers: dict[str, str] = dict(FORM)
    if signature == "valid":
        headers["Signature"] = sign_zadarma(fields)
    elif signature is not None:
        headers["Signature"] = signature
    response = build_calls_http_client(setup.testbed).post(
        NOTIFICATIONS, content=encode_form(fields), headers=headers
    )
    setup.testbed.run_worker()
    return response


@pytest.fixture
def setup() -> VoiceSetup:
    voice_setup = build_voice_setup()
    save_call_settings(voice_setup)
    connect_whatsapp(voice_setup)
    add_staff_chat(voice_setup, language="ka")
    return voice_setup


class TestZadarmaNotifications:
    def test_the_address_check_echoes_the_token(self, setup: VoiceSetup) -> None:
        client = build_calls_http_client(setup.testbed)

        echoed = client.get(NOTIFICATIONS, params={"zd_echo": "a1B2_c3-D4"})
        missing = client.get(NOTIFICATIONS)
        odd = client.get(NOTIFICATIONS, params={"zd_echo": "<script>"})

        assert echoed.status_code == 200
        assert echoed.text == "a1B2_c3-D4"
        assert missing.status_code == 422
        assert odd.status_code == 422

    def test_a_call_nobody_answered_is_texted_and_reported(
        self, setup: VoiceSetup
    ) -> None:
        response = notify(setup, zadarma_form("no answer", duration="25"))

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "recorded"
        assert body["text_back_status"] == "queued"
        [missed] = missed_calls(setup)
        assert str(missed.id) == body["missed_call_id"]
        assert missed.source is MissedCallSource.PBX
        assert missed.reason is MissedCallReason.NO_ANSWER
        assert str(missed.provider_call_id) == "in_1790856000.1"
        assert missed.caller_phone_number == CALLER
        assert int(missed.called_at) == int(setup.testbed.clock.now_microseconds()) - (
            25 * 1_000_000
        )
        assert missed.status is TextBackStatus.SENT
        assert len(whatsapp_templates(setup)) == 1
        [text] = staff_texts(setup)
        lines = str(text.text).split("\n")
        assert lines[0] == "გამოტოვებული ზარი · Funicular VR"
        assert lines[2] == "მიზეზი: არავინ უპასუხა"

    @pytest.mark.parametrize(
        ("disposition", "reason"),
        [
            ("busy", MissedCallReason.BUSY),
            ("cancel", MissedCallReason.ABANDONED),
            ("NO_ANSWER", MissedCallReason.NO_ANSWER),
            ("no money", MissedCallReason.LINE_FAILED),
        ],
    )
    def test_how_the_call_ended(
        self, setup: VoiceSetup, disposition: str, reason: MissedCallReason
    ) -> None:
        notify(setup, zadarma_form(disposition))

        [missed] = missed_calls(setup)
        assert missed.reason is reason

    def test_answered_and_other_events_are_ignored(self, setup: VoiceSetup) -> None:
        answered = notify(setup, zadarma_form("answered"))
        started = notify(setup, zadarma_form(event="NOTIFY_START"))

        assert answered.json() == {
            "status": "ignored",
            "missed_call_id": None,
            "text_back_status": None,
        }
        assert started.json()["status"] == "ignored"
        assert missed_calls(setup) == []

    def test_the_same_notification_twice_is_handled_once(
        self, setup: VoiceSetup
    ) -> None:
        notify(setup, zadarma_form())

        again = notify(setup, zadarma_form())

        assert again.json()["status"] == "duplicate"
        assert again.json()["text_back_status"] == "sent"
        assert len(missed_calls(setup)) == 1
        assert len(whatsapp_templates(setup)) == 1
        assert len(staff_texts(setup)) == 1

    def test_a_line_no_business_has_is_ignored(self, setup: VoiceSetup) -> None:
        response = notify(setup, zadarma_form(called_did="+995322999999"))

        assert response.json()["status"] == "ignored"
        assert missed_calls(setup) == []

    def test_a_notification_without_a_call_id_is_refused(
        self, setup: VoiceSetup
    ) -> None:
        response = notify(setup, zadarma_form(pbx_call_id=" "))

        assert response.status_code == 422
        assert missed_calls(setup) == []

    @pytest.mark.parametrize("signature", [None, "bm90IGEgc2lnbmF0dXJl"])
    def test_an_unsigned_or_forged_notification_is_refused(
        self, setup: VoiceSetup, signature: str | None
    ) -> None:
        response = notify(setup, zadarma_form(), signature=signature)

        assert response.status_code == 401
        assert missed_calls(setup) == []

    def test_without_the_api_secret_every_notification_is_refused(self) -> None:
        setup = build_voice_setup(settings=build_settings(ZADARMA_API_SECRET=""))

        response = notify(setup, zadarma_form())

        assert response.status_code == 401


class TestZadarmaReading:
    def test_the_raw_digest_signature_is_accepted_too(self) -> None:
        fields = zadarma_form()
        signed = (
            fields["caller_id"] + fields["called_did"] + fields["call_start"]
        ).encode()
        raw = base64.b64encode(
            hmac.new(ZADARMA_API_SECRET.encode(), signed, hashlib.sha1).digest()
        ).decode()

        assert is_valid_zadarma_signature(ZADARMA_API_SECRET, fields, raw)
        assert not is_valid_zadarma_signature("another-secret", fields, raw)
        assert not is_valid_zadarma_signature(
            ZADARMA_API_SECRET, {**fields, "event": "NOTIFY_OUT_END"}, raw
        )

    def test_form_fields(self) -> None:
        assert read_form_fields(b"event=NOTIFY_END&caller_id=%2B995&caller_id=2") == {
            "event": "NOTIFY_END",
            "caller_id": "+995",
        }
        assert read_form_fields(b"\xff\xfe") == {}

    def test_dispositions(self) -> None:
        assert read_missed_reason(" No  Answer ") is MissedCallReason.NO_ANSWER
        assert read_missed_reason("answered") is None
        assert read_missed_reason("") is None

    def test_an_unreadable_ring_time_counts_as_none(self, setup: VoiceSetup) -> None:
        notify(setup, zadarma_form(duration="soon"))

        [missed] = missed_calls(setup)
        assert missed.called_at == setup.testbed.clock.now_microseconds()
