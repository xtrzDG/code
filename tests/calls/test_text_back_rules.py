"""Which callers who did not get through are texted, how and in which language."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackChannel,
    TextBackSkipReason,
    TextBackStatus,
)
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.calls.missed_calls import MissedCallReport, RegisteredMissedCall
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.conversations.strings import ChannelUserId, ProviderCallId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.use_cases.voice.missed_calls.text_back_rules import (
    BUSINESS_DAILY_LIMIT,
    DAY_WINDOW,
)
from app.utilities.calls.call_follow_up_keys import business_text_back_key
from tests.calls.call_steps import (
    WHATSAPP_NUMBER_ID,
    connect_whatsapp,
    save_call_settings,
)
from tests.channels.voice_setup import (
    ASSISTANT_LINE,
    CALLER,
    VoiceSetup,
    build_voice_setup,
)

DAY_SECONDS: int = 24 * 60 * 60


def ago(setup: VoiceSetup, seconds: int) -> Microseconds:
    return Microseconds(int(setup.testbed.clock.now_microseconds()) - seconds * 10**6)


def missed_report(
    setup: VoiceSetup,
    provider_call_id: str = "in_1",
    caller: str | None = CALLER,
    language: str | None = None,
    seconds_ago: int = 20,
    assistant_number: str = ASSISTANT_LINE,
) -> MissedCallReport:
    return MissedCallReport(
        source=MissedCallSource.PBX,
        provider_call_id=ProviderCallId(provider_call_id),
        reason=MissedCallReason.NO_ANSWER,
        called_at=ago(setup, seconds_ago),
        assistant_number=RawPhoneNumberInput(assistant_number),
        caller_number=None if caller is None else RawPhoneNumberInput(caller),
        language=None if language is None else LanguageTag(language),
    )


def register(setup: VoiceSetup, report: MissedCallReport) -> RegisteredMissedCall:
    registered = setup.testbed.register_missed_call.run(report)
    assert registered is not None
    return registered


def skip_reason(
    setup: VoiceSetup,
    caller: str | None = CALLER,
    seconds_ago: int = 20,
) -> TextBackSkipReason | None:
    report = missed_report(setup, caller=caller, seconds_ago=seconds_ago)
    return register(setup, report).missed_call.skip_reason


def add_whatsapp_conversation(
    setup: VoiceSetup,
    seconds_ago: int,
    status: ConversationStatus = ConversationStatus.OPEN,
) -> None:
    setup.testbed.conversation_repo.save(
        ConversationDocument(
            business_id=setup.business.id,
            contact_id=setup.contact.id,
            assistant_version_id=setup.conversation.assistant_version_id,
            channel=ChannelKind.WHATSAPP,
            channel_user_id=ChannelUserId("995599123456"),
            status=status,
            last_message_at=ago(setup, seconds_ago),
        )
    )


@pytest.fixture
def setup() -> VoiceSetup:
    voice_setup = build_voice_setup()
    save_call_settings(voice_setup)
    connect_whatsapp(voice_setup)
    return voice_setup


class TestWhoIsTexted:
    def test_a_caller_is_texted_on_whatsapp(self, setup: VoiceSetup) -> None:
        registered = register(setup, missed_report(setup))

        assert registered.is_new is True
        assert registered.missed_call.status is TextBackStatus.QUEUED
        assert registered.missed_call.channel is TextBackChannel.WHATSAPP
        assert registered.missed_call.caller_phone_number == CALLER

    def test_text_backs_are_off_until_the_owner_turns_them_on(self) -> None:
        setup = build_voice_setup()

        assert skip_reason(setup) is TextBackSkipReason.TURNED_OFF

    def test_a_hidden_number_is_not_texted(self, setup: VoiceSetup) -> None:
        assert skip_reason(setup, caller=None) is TextBackSkipReason.NO_CALLER_NUMBER

    def test_an_assistant_that_is_not_live_does_not_text(
        self, setup: VoiceSetup
    ) -> None:
        setup.business.status = BusinessStatus.PAUSED
        setup.testbed.business_repo.save(setup.business)

        assert skip_reason(setup) is TextBackSkipReason.NOT_LIVE

    def test_a_report_hours_late_is_not_texted(self, setup: VoiceSetup) -> None:
        assert (
            skip_reason(setup, seconds_ago=3 * 60 * 60) is TextBackSkipReason.TOO_LATE
        )

    def test_without_a_template_sms_takes_over(self, setup: VoiceSetup) -> None:
        save_call_settings(setup, template_name=None)

        missed = register(setup, missed_report(setup)).missed_call

        assert missed.channel is TextBackChannel.SMS

    def test_a_failing_whatsapp_number_is_still_tried(self, setup: VoiceSetup) -> None:
        [channel] = [
            channel
            for channel in setup.testbed.channel_repo.list_by_business(
                setup.business.id
            )
            if str(channel.external_id) == WHATSAPP_NUMBER_ID
        ]
        channel.status = ChannelStatus.ERROR
        setup.testbed.channel_repo.save(channel)

        missed = register(setup, missed_report(setup)).missed_call

        assert missed.channel is TextBackChannel.WHATSAPP

    def test_no_channel_at_all(self, setup: VoiceSetup) -> None:
        save_call_settings(setup, template_name=None, is_sms_fallback_enabled=False)

        assert skip_reason(setup) is TextBackSkipReason.NO_CHANNEL

    def test_a_customer_who_opted_out_is_not_texted(self, setup: VoiceSetup) -> None:
        setup.contact.opted_out_channels = [ChannelKind.PHONE]
        setup.testbed.contact_repo.save(setup.contact)

        assert skip_reason(setup) is TextBackSkipReason.OPTED_OUT

    def test_a_customer_writing_on_whatsapp_is_not_texted(
        self, setup: VoiceSetup
    ) -> None:
        add_whatsapp_conversation(setup, seconds_ago=3600)

        assert skip_reason(setup) is TextBackSkipReason.IN_CONVERSATION

    def test_a_conversation_staff_still_own_counts(self, setup: VoiceSetup) -> None:
        add_whatsapp_conversation(
            setup, seconds_ago=3 * DAY_SECONDS, status=ConversationStatus.HANDOFF
        )

        assert skip_reason(setup) is TextBackSkipReason.IN_CONVERSATION

    def test_an_old_or_closed_conversation_does_not(self, setup: VoiceSetup) -> None:
        add_whatsapp_conversation(setup, seconds_ago=3 * DAY_SECONDS)
        add_whatsapp_conversation(
            setup, seconds_ago=60, status=ConversationStatus.CLOSED
        )

        assert skip_reason(setup) is None


class TestLimits:
    def test_one_text_back_per_caller_and_day(self, setup: VoiceSetup) -> None:
        register(setup, missed_report(setup, "in_1"))

        again = register(setup, missed_report(setup, "in_2")).missed_call
        other = register(
            setup, missed_report(setup, "in_3", caller="+995599765432")
        ).missed_call
        setup.testbed.clock.advance(2 * DAY_SECONDS)
        next_day = register(setup, missed_report(setup, "in_4")).missed_call

        assert again.skip_reason is TextBackSkipReason.ALREADY_TEXTED
        assert other.status is TextBackStatus.QUEUED
        assert next_day.status is TextBackStatus.QUEUED

    def test_a_daily_cap_per_business(self, setup: VoiceSetup) -> None:
        cap = RateLimitCounter(
            key=business_text_back_key(setup.business.id), limit=BUSINESS_DAILY_LIMIT
        )
        for _ in range(int(BUSINESS_DAILY_LIMIT)):
            setup.testbed.rate_limits.try_acquire_all(
                [cap], DAY_WINDOW, setup.testbed.clock.now_microseconds()
            )

        assert skip_reason(setup) is TextBackSkipReason.DAILY_LIMIT

    def test_the_same_call_reported_again_changes_nothing(
        self, setup: VoiceSetup
    ) -> None:
        first = register(setup, missed_report(setup))

        again = register(setup, missed_report(setup, language="ru"))

        assert again.is_new is False
        assert again.missed_call == first.missed_call

    def test_a_line_no_business_has_is_ignored(self, setup: VoiceSetup) -> None:
        report = missed_report(setup, assistant_number="+995322999999")

        assert setup.testbed.register_missed_call.run(report) is None
        assert (
            setup.testbed.register_missed_call.run(
                missed_report(setup, assistant_number="not a number")
            )
            is None
        )


class TestLanguage:
    @pytest.mark.parametrize(
        ("caller", "detected", "expected"),
        [
            (CALLER, "en", "en"),
            (CALLER, None, "ka"),
            ("+79161234567", None, "ru"),
            # Polish is not spoken here; English, Poland's other one, is.
            ("+48512345678", None, "en"),
            ("599 76 54 32", None, "ka"),
        ],
    )
    def test_the_callers_language(
        self,
        setup: VoiceSetup,
        caller: str,
        detected: str | None,
        expected: str,
    ) -> None:
        missed = register(
            setup, missed_report(setup, caller=caller, language=detected)
        ).missed_call

        assert str(missed.language) == expected

    def test_a_hidden_number_gets_the_business_language(
        self, setup: VoiceSetup
    ) -> None:
        missed = register(setup, missed_report(setup, caller=None)).missed_call

        assert str(missed.language) == "ka"
