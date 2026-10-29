"""
The suppression list stops every message a customer did not ask for, also
for a contact that never sent STOP itself (the one an erasure left behind
is gone; the same number or account comes back as a new contact): booking
reminders, messages after a missed call and requests for feedback.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackSkipReason,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.feedback import FeedbackRequestStatus, FeedbackSkipReason
from app.schemas.dto.calls.missed_calls import MissedCallReport
from app.schemas.typings.conversations.strings import ChannelUserId, ProviderCallId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.utilities.privacy.suppressed_identities import (
    channel_identity,
    phone_identity,
)
from tests.calls.call_steps import connect_whatsapp, save_call_settings
from tests.channels.voice_setup import ASSISTANT_LINE, CALLER, build_voice_setup
from tests.feedback.feedback_setup import FeedbackSetup
from tests.operations.reminder_scene import ReminderScene


def test_a_listed_whatsapp_account_gets_no_request_for_feedback() -> None:
    setup = FeedbackSetup()
    contact = setup.add_customer()
    setup.customer_wrote(contact, ChannelKind.WHATSAPP, 1)
    setup.add_visit(contact)
    setup.suppression_list.suppress(
        setup.business.id,
        [channel_identity(ChannelKind.WHATSAPP, ChannelUserId("995599123456"))],
        Microseconds(0),
    )

    report = setup.run()

    assert int(report.processed_count) == 0
    request = setup.only_request()
    assert request.status is FeedbackRequestStatus.SKIPPED
    assert request.skip_reason is FeedbackSkipReason.OPTED_OUT
    assert setup.outbox() == []


def test_an_unlisted_customer_is_still_asked() -> None:
    setup = FeedbackSetup()
    contact = setup.add_customer()
    setup.customer_wrote(contact, ChannelKind.WHATSAPP, 1)
    setup.add_visit(contact)
    setup.suppression_list.suppress(
        setup.business.id,
        [phone_identity(E164PhoneNumber("+995599000000"))],
        Microseconds(0),
    )

    report = setup.run()

    assert int(report.processed_count) == 1


def test_a_listed_number_gets_no_reminder() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.WHATSAPP: "995555123456"})
    scene.customer_wrote(contact, ChannelKind.WHATSAPP, hours_ago=3)
    booking = scene.add_booking(contact, "2026-10-05T15:00:00+00:00")
    scene.suppression_list.suppress(
        scene.business.id,
        [phone_identity(E164PhoneNumber("+995555123456"))],
        Microseconds(0),
    )

    scene.run()

    assert scene.sender.sent == []
    assert scene.sender.templates == []
    assert scene.stored(booking).reminder_sent_at is None


def test_a_listed_caller_without_a_contact_gets_no_text_back() -> None:
    setup = build_voice_setup()
    save_call_settings(setup)
    connect_whatsapp(setup)
    setup.testbed.contact_repo.delete(setup.business.id, setup.contact.id)
    setup.testbed.suppression_list.suppress(
        setup.business.id,
        [phone_identity(E164PhoneNumber(CALLER))],
        Microseconds(0),
    )

    registered = setup.testbed.register_missed_call.run(
        MissedCallReport(
            source=MissedCallSource.PBX,
            provider_call_id=ProviderCallId("in_listed"),
            reason=MissedCallReason.NO_ANSWER,
            called_at=setup.testbed.clock.now_microseconds(),
            assistant_number=RawPhoneNumberInput(ASSISTANT_LINE),
            caller_number=RawPhoneNumberInput(CALLER),
        )
    )

    assert registered is not None
    assert registered.missed_call.skip_reason is TextBackSkipReason.OPTED_OUT
    assert registered.missed_call.caller_phone_number == CALLER
