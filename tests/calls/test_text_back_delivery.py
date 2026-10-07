"""
The worker sends each text-back once: WhatsApp, else SMS when WhatsApp
refuses it for good; a temporary failure is tried again, the last attempt
gives up, and a message hours late is not sent.
"""

from typing import Any

import pytest

from app.schemas.constants.calls import (
    MissedCallSource,
    TextBackChannel,
    TextBackStatus,
)
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ProviderRejectedMessageError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calls.prefixed_id import MissedCallId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.platform.prefixed_id import QueuedJobId
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
from tests.channels.voice_setup import (
    CALLER,
    VoiceSetup,
    build_voice_setup,
)

TEMPLATE_MISSING: dict[str, Any] = {
    "error": {"code": 132001, "message": "(#132001) Template name does not exist"}
}
META_OUTAGE: dict[str, Any] = {
    "error": {"code": 2, "message": "Service temporarily unavailable"}
}
SENT: dict[str, Any] = {"messages": [{"id": "wamid.7"}]}


def only_missed_call(setup: VoiceSetup) -> MissedCallDocument:
    [missed] = missed_calls(setup)
    return missed


def retry_later(setup: VoiceSetup, times: int = 1) -> None:
    """Five minutes later, run what is due (one retry of the outbox each)."""

    for _ in range(times):
        setup.testbed.clock.advance(5 * 60)
        setup.testbed.run_worker()


@pytest.fixture
def setup() -> VoiceSetup:
    voice_setup = build_voice_setup()
    save_call_settings(voice_setup)
    connect_whatsapp(voice_setup)
    return voice_setup


class TestWhatsApp:
    def test_a_new_caller_becomes_a_contact_with_a_conversation(
        self, setup: VoiceSetup
    ) -> None:
        report_missed_call(setup, caller="+995599765432")
        setup.testbed.run_worker()

        missed = only_missed_call(setup)
        assert missed.status is TextBackStatus.SENT
        assert missed.sent_at == setup.testbed.clock.now_microseconds()
        assert missed.conversation_id is not None
        conversation = setup.testbed.conversation_repo.get(
            setup.business.id, missed.conversation_id
        )
        assert conversation is not None
        contact = setup.testbed.contact_repo.get(
            setup.business.id, conversation.contact_id
        )
        assert contact is not None
        assert contact.verified_phone_number == "+995599765432"
        assert {str(identity.channel) for identity in contact.channel_identities} == {
            "phone",
            "whatsapp",
        }

    def test_a_refused_template_goes_by_sms(self, setup: VoiceSetup) -> None:
        setup.testbed.meta_transport.respond(
            "POST", r"/messages$", TEMPLATE_MISSING, status_code=404
        )
        report_missed_call(setup)
        setup.testbed.run_worker()

        missed = only_missed_call(setup)
        assert missed.status is TextBackStatus.SENT
        assert missed.channel is TextBackChannel.SMS
        assert missed.last_error is not None
        assert "132001" in str(missed.last_error)
        # Georgian first, then English (Meta may have only that translation).
        assert [
            template["template"]["language"]["code"]
            for template in whatsapp_templates(setup)
        ] == ["ka", "en"]
        [(recipient, text)] = setup.testbed.sms_client.sent
        assert recipient == CALLER
        assert str(text).startswith("Funicular VR: ბოდიშს გიხდით")

    def test_a_refused_template_without_sms_fails(self, setup: VoiceSetup) -> None:
        save_call_settings(setup, is_sms_fallback_enabled=False)
        setup.testbed.meta_transport.respond(
            "POST", r"/messages$", TEMPLATE_MISSING, status_code=404
        )
        report_missed_call(setup)
        setup.testbed.run_worker()

        missed = only_missed_call(setup)
        assert missed.status is TextBackStatus.FAILED
        assert setup.testbed.sms_client.sent == []

    def test_an_outage_is_tried_again(self, setup: VoiceSetup) -> None:
        setup.testbed.meta_transport.respond_in_turn(
            "POST",
            r"/messages$",
            [(500, META_OUTAGE), (500, META_OUTAGE), (200, SENT)],
        )
        report_missed_call(setup)
        setup.testbed.run_worker()
        assert only_missed_call(setup).status is TextBackStatus.QUEUED

        # The outbox tries again after 10 s, then 20 s.
        retry_later(setup, times=2)

        missed = only_missed_call(setup)
        assert missed.status is TextBackStatus.SENT
        assert missed.channel is TextBackChannel.WHATSAPP
        assert len(whatsapp_templates(setup)) == 3

    def test_the_last_attempt_gives_up(self, setup: VoiceSetup) -> None:
        save_call_settings(setup, is_sms_fallback_enabled=False)
        setup.testbed.meta_transport.respond(
            "POST", r"/messages$", META_OUTAGE, status_code=500
        )
        report_missed_call(setup)
        setup.testbed.run_worker()

        retry_later(setup, times=10)

        missed = only_missed_call(setup)
        assert missed.status is TextBackStatus.FAILED
        assert missed.last_error is not None
        # The outbox's eight attempts over about 21 minutes; an outage is
        # not a missing translation, so none of them falls back to English.
        assert len(whatsapp_templates(setup)) == 8

    def test_a_message_hours_late_is_not_sent(self, setup: VoiceSetup) -> None:
        setup.testbed.meta_transport.respond(
            "POST", r"/messages$", META_OUTAGE, status_code=500
        )
        report_missed_call(setup)
        setup.testbed.run_worker()
        setup.testbed.meta_transport.respond("POST", r"/messages$", SENT)
        setup.testbed.clock.advance(3 * 60 * 60)

        setup.testbed.run_worker()

        missed = only_missed_call(setup)
        assert missed.status is TextBackStatus.SKIPPED
        assert str(missed.skip_reason) == "too_late"


class TestSms:
    @pytest.fixture
    def sms_setup(self) -> VoiceSetup:
        voice_setup = build_voice_setup()
        save_call_settings(voice_setup, template_name=None)
        return voice_setup

    def test_sms_without_a_whatsapp_template(self, sms_setup: VoiceSetup) -> None:
        report_missed_call(sms_setup)
        sms_setup.testbed.run_worker()

        missed = only_missed_call(sms_setup)
        assert missed.status is TextBackStatus.SENT
        assert missed.channel is TextBackChannel.SMS
        assert missed.conversation_id is None
        [(recipient, _)] = sms_setup.testbed.sms_client.sent
        assert recipient == CALLER

    def test_a_temporary_sms_failure_is_tried_again(
        self, sms_setup: VoiceSetup
    ) -> None:
        sms_setup.testbed.sms_client.failure = ExternalServiceError("SMS is down.")
        report_missed_call(sms_setup)
        sms_setup.testbed.run_worker()
        assert only_missed_call(sms_setup).status is TextBackStatus.QUEUED

        sms_setup.testbed.sms_client.failure = None
        retry_later(sms_setup)

        assert only_missed_call(sms_setup).status is TextBackStatus.SENT

    def test_a_refused_sms_fails(self, sms_setup: VoiceSetup) -> None:
        sms_setup.testbed.sms_client.failure = ProviderRejectedMessageError(
            "Unknown number."
        )
        report_missed_call(sms_setup)
        sms_setup.testbed.run_worker()

        missed = only_missed_call(sms_setup)
        assert missed.status is TextBackStatus.FAILED
        assert "Unknown number." in str(missed.last_error)


class TestJobs:
    def test_a_job_runs_once_per_missed_call(self, setup: VoiceSetup) -> None:
        report_missed_call(setup)
        setup.testbed.run_worker()
        missed = only_missed_call(setup)

        again = setup.testbed.send_text_back.run(job(missed.id, setup.business.id))
        unknown = setup.testbed.send_text_back.run(
            job(
                missed_call_id_of(
                    setup.business.id, MissedCallSource.PBX, ProviderCallId("other")
                ),
                setup.business.id,
            )
        )
        unscoped = setup.testbed.send_text_back.run(job(missed.id, None))

        assert int(again.processed_count) == 0
        assert int(unknown.processed_count) == 0
        assert int(unscoped.processed_count) == 0
        assert len(whatsapp_templates(setup)) == 1


def job(missed_call_id: MissedCallId, business_id: BusinessId | None) -> QueuedJobInput:
    return QueuedJobInput(
        job_id=QueuedJobId(),
        job_name=SEND_TEXT_BACK_JOB,
        payload=encode_text_back_payload(missed_call_id),
        business_id=business_id,
    )
