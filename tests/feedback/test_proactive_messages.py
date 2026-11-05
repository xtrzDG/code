"""
Every message a customer did not ask for honours their STOP, in any
channel, and the shared daily cap per customer: booking reminders and
messages after a missed call as well as feedback requests.
"""

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackSkipReason,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.calls.missed_calls import MissedCallReport
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.utilities.channels.proactive_limits import (
    PROACTIVE_DAILY_LIMIT,
    PROACTIVE_WINDOW,
    proactive_message_counter,
)
from tests.calls.call_steps import connect_whatsapp, save_call_settings
from tests.channels.voice_setup import ASSISTANT_LINE, CALLER, build_voice_setup
from tests.operations.builders import DEFAULT_NOW
from tests.operations.fakes import to_microseconds
from tests.operations.reminder_scene import ReminderScene


def use_up_the_daily_cap(
    rate_limits: RequestRateLimitRegistryContract,
    business_id: BusinessId,
    contact_id: ContactId,
    now: Microseconds,
) -> None:
    counter = proactive_message_counter(business_id, contact_id)
    for _ in range(int(PROACTIVE_DAILY_LIMIT)):
        assert rate_limits.try_acquire_all([counter], PROACTIVE_WINDOW, now) is None


class TestReminders:
    def test_a_customer_who_sent_stop_anywhere_gets_no_reminder(self) -> None:
        scene = ReminderScene()
        contact = scene.add_customer({ChannelKind.WHATSAPP: "995555123456"})
        contact.opted_out_channels = [ChannelKind.TELEGRAM]
        scene.world.contact_repo.save(contact)
        scene.customer_wrote(contact, ChannelKind.WHATSAPP, hours_ago=3)
        booking = scene.add_booking(contact, "2026-10-05T15:00:00+00:00")

        report = scene.run()

        assert int(report.processed_count) == 0
        assert scene.sender.sent == []
        assert scene.sender.templates == []
        assert scene.stored(booking).reminder_sent_at is None

    def test_the_shared_daily_cap_holds_back_a_reminder(self) -> None:
        scene = ReminderScene()
        contact = scene.add_customer({ChannelKind.WHATSAPP: "995555123456"})
        scene.customer_wrote(contact, ChannelKind.WHATSAPP, hours_ago=3)
        booking = scene.add_booking(contact, "2026-10-05T15:00:00+00:00")
        use_up_the_daily_cap(
            scene.rate_limits,
            scene.business.id,
            contact.id,
            to_microseconds(DEFAULT_NOW),
        )

        scene.run()

        assert scene.sender.sent == []
        assert scene.stored(booking).reminder_sent_at is None

    def test_a_reminder_counts_against_the_cap(self) -> None:
        scene = ReminderScene()
        contact = scene.add_customer({ChannelKind.WHATSAPP: "995555123456"})
        scene.customer_wrote(contact, ChannelKind.WHATSAPP, hours_ago=3)
        scene.add_booking(contact, "2026-10-05T15:00:00+00:00")

        scene.run()

        counter = proactive_message_counter(scene.business.id, contact.id)
        now = to_microseconds(DEFAULT_NOW)
        allowed = [
            scene.rate_limits.try_acquire_all([counter], PROACTIVE_WINDOW, now)
            for _ in range(int(PROACTIVE_DAILY_LIMIT))
        ]
        assert allowed[:-1] == [None] * (int(PROACTIVE_DAILY_LIMIT) - 1)
        assert allowed[-1] == counter.key


class TestTextBacks:
    def report(self) -> MissedCallReport:
        return MissedCallReport(
            source=MissedCallSource.PBX,
            provider_call_id=ProviderCallId("in_1"),
            reason=MissedCallReason.NO_ANSWER,
            called_at=Microseconds(0),
            assistant_number=RawPhoneNumberInput(ASSISTANT_LINE),
            caller_number=RawPhoneNumberInput(CALLER),
        )

    def test_the_shared_daily_cap_holds_back_a_text_back(self) -> None:
        setup = build_voice_setup()
        save_call_settings(setup)
        connect_whatsapp(setup)
        now = setup.testbed.clock.now_microseconds()
        use_up_the_daily_cap(
            setup.testbed.rate_limits, setup.business.id, setup.contact.id, now
        )

        registered = setup.testbed.register_missed_call.run(
            self.report().model_copy(update={"called_at": now})
        )

        assert registered is not None
        assert registered.missed_call.skip_reason is TextBackSkipReason.DAILY_LIMIT

    def test_a_stop_sent_in_a_messenger_also_stops_text_backs(self) -> None:
        setup = build_voice_setup()
        save_call_settings(setup)
        connect_whatsapp(setup)
        setup.contact.opted_out_channels = [ChannelKind.WHATSAPP]
        setup.testbed.contact_repo.save(setup.contact)

        registered = setup.testbed.register_missed_call.run(
            self.report().model_copy(
                update={"called_at": setup.testbed.clock.now_microseconds()}
            )
        )

        assert registered is not None
        assert registered.missed_call.skip_reason is TextBackSkipReason.OPTED_OUT
