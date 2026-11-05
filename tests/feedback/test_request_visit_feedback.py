"""
The job that asks customers how their visit went: once per visit, after the
owner's delay, in the customer's messenger and language, never to a
customer who opted out, and only where the request can be delivered.
"""

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.constants.feedback import FeedbackRequestStatus, FeedbackSkipReason
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.typings.platform.constrained_integers import RateWindowSeconds
from app.utilities.channels.proactive_limits import proactive_message_counter
from tests.feedback.feedback_setup import TELEGRAM_USER, WHATSAPP_USER, FeedbackSetup


@pytest.fixture
def setup() -> FeedbackSetup:
    return FeedbackSetup()


class TestAsking:
    def test_a_customer_who_wrote_today_is_asked_in_free_text(
        self, setup: FeedbackSetup
    ) -> None:
        contact = setup.add_customer()
        conversation = setup.customer_wrote(contact, ChannelKind.WHATSAPP, 3)
        visit = setup.add_visit(contact, ended_minutes_ago=150)

        report = setup.run()

        assert int(report.processed_count) == 1
        request = setup.only_request()
        assert request.status is FeedbackRequestStatus.SENT
        assert request.booking_id == visit.id
        assert request.channel is ChannelKind.WHATSAPP
        assert str(request.language) == "ka"
        assert request.review_token is not None
        assert request.sent_at == setup.testbed.clock.now_microseconds()
        assert request.conversation_id == conversation.id
        [message] = setup.outbox()
        assert message.kind is OutboundMessageKind.CUSTOMER_REPLY
        assert message.template is None
        assert message.feedback_request_id == request.id
        assert message.customer is not None
        assert str(message.customer.channel_user_id) == WHATSAPP_USER
        assert "Café Rustaveli" in str(message.text)
        assert "სტოპ" in str(message.text)
        # Staff and the assistant see what was asked, in the same conversation.
        shown = setup.testbed.message_repo.list_by_conversation(
            setup.business.id, conversation.id
        )[-1]
        assert shown.direction is MessageDirection.OUTBOUND
        assert shown.author is MessageAuthor.STAFF
        assert shown.text == message.text
        [event] = setup.testbed.live_events.events
        assert event.event is LiveEventKind.CONVERSATION_MESSAGE
        assert event.ids == (str(conversation.id),)

    def test_outside_the_window_the_approved_template_names_the_business(
        self, setup: FeedbackSetup
    ) -> None:
        contact = setup.add_customer(language="ru")
        setup.add_visit(contact)

        setup.run()

        request = setup.only_request()
        assert request.status is FeedbackRequestStatus.SENT
        [message] = setup.outbox()
        assert message.template is not None
        assert str(message.template.name) == "visit_feedback"
        assert str(message.template.language_code) == "ru"
        assert [str(value) for value in message.template.body_parameters] == [
            "Café Rustaveli"
        ]
        assert str(message.text).startswith("Здравствуйте, это Café Rustaveli!")
        # A new conversation pinned to the live version shows the request.
        assert request.conversation_id is not None
        conversation = setup.testbed.conversation_repo.get(
            setup.business.id, request.conversation_id
        )
        assert conversation is not None
        assert conversation.channel is ChannelKind.WHATSAPP
        assert (
            conversation.assistant_version_id
            == setup.business.published_assistant_version_id
        )

    def test_the_booking_language_wins_over_the_customer_language(
        self, setup: FeedbackSetup
    ) -> None:
        contact = setup.add_customer(language="ka")
        setup.add_visit(contact, language="en")

        setup.run()

        assert str(setup.only_request().language) == "en"
        assert str(setup.outbox()[0].text).startswith("Hello from Café Rustaveli!")

    def test_telegram_needs_no_window_and_goes_first_for_its_bookings(
        self, setup: FeedbackSetup
    ) -> None:
        setup.connect_telegram()
        contact = setup.add_customer(
            channels=(ChannelKind.WHATSAPP, ChannelKind.TELEGRAM)
        )
        setup.add_visit(contact, source_channel=ChannelKind.TELEGRAM)

        setup.run()

        request = setup.only_request()
        assert request.channel is ChannelKind.TELEGRAM
        [message] = setup.outbox()
        assert message.template is None
        assert message.customer is not None
        assert str(message.customer.channel_user_id) == TELEGRAM_USER

    def test_a_rerun_asks_once(self, setup: FeedbackSetup) -> None:
        contact = setup.add_customer()
        setup.add_visit(contact)

        first = setup.run()
        setup.testbed.clock.advance(10 * 60)
        second = setup.run()

        assert int(first.processed_count) == 1
        assert int(second.processed_count) == 0
        assert len(setup.requests()) == 1
        assert len(setup.outbox()) == 1


class TestNotAsking:
    def test_no_request_goes_to_opted_out_contacts(self, setup: FeedbackSetup) -> None:
        contact = setup.add_customer(opted_out=(ChannelKind.TELEGRAM,))
        setup.customer_wrote(contact, ChannelKind.WHATSAPP, 1)
        setup.add_visit(contact)

        report = setup.run()

        assert int(report.processed_count) == 0
        request = setup.only_request()
        assert request.status is FeedbackRequestStatus.SKIPPED
        assert request.skip_reason is FeedbackSkipReason.OPTED_OUT
        assert request.review_token is None
        assert setup.outbox() == []

    def test_a_closed_window_without_a_template_is_not_asked(
        self, setup: FeedbackSetup
    ) -> None:
        setup.save_settings(template_name=None)
        contact = setup.add_customer()
        setup.customer_wrote(contact, ChannelKind.WHATSAPP, 30)
        setup.add_visit(contact)

        setup.run()

        request = setup.only_request()
        assert request.skip_reason is FeedbackSkipReason.WINDOW_CLOSED
        assert setup.outbox() == []

    def test_a_customer_known_only_by_phone_has_no_channel(
        self, setup: FeedbackSetup
    ) -> None:
        contact = setup.add_customer(channels=(ChannelKind.PHONE,))
        setup.add_visit(contact, source_channel=ChannelKind.PHONE)

        setup.run()

        assert setup.only_request().skip_reason is FeedbackSkipReason.NO_CHANNEL
        assert setup.outbox() == []

    def test_two_visits_the_same_day_are_asked_about_once(
        self, setup: FeedbackSetup
    ) -> None:
        contact = setup.add_customer()
        setup.add_visit(contact, ended_minutes_ago=200)
        setup.add_visit(contact, ended_minutes_ago=130)

        setup.run()

        statuses = sorted(
            (request.status, request.skip_reason) for request in setup.requests()
        )
        assert statuses == [
            (FeedbackRequestStatus.SENT, None),
            (FeedbackRequestStatus.SKIPPED, FeedbackSkipReason.ALREADY_ASKED),
        ]
        assert len(setup.outbox()) == 1

    def test_the_shared_daily_cap_of_unrequested_messages_holds(
        self, setup: FeedbackSetup
    ) -> None:
        contact = setup.add_customer()
        setup.add_visit(contact)
        counter = proactive_message_counter(setup.business.id, contact.id)
        now = setup.testbed.clock.now_microseconds()
        for _ in range(int(counter.limit)):
            assert (
                setup.rate_limits.try_acquire_all(
                    [counter], RateWindowSeconds(86_400), now
                )
                is None
            )

        setup.run()

        assert setup.only_request().skip_reason is FeedbackSkipReason.DAILY_LIMIT
        assert setup.outbox() == []

    @pytest.mark.parametrize("minutes_ago", [60, 119, 8 * 60 + 1])
    def test_visits_not_yet_due_or_long_past_are_left_alone(
        self, setup: FeedbackSetup, minutes_ago: int
    ) -> None:
        contact = setup.add_customer()
        setup.add_visit(contact, ended_minutes_ago=minutes_ago)

        setup.run()

        assert setup.requests() == []

    @pytest.mark.parametrize(
        ("status", "is_sandbox"),
        [
            (BookingStatus.NO_SHOW, False),
            (BookingStatus.CANCELLED, False),
            (BookingStatus.PENDING, False),
            (BookingStatus.COMPLETED, True),
        ],
    )
    def test_no_shows_cancellations_and_tests_are_not_visits(
        self, setup: FeedbackSetup, status: BookingStatus, is_sandbox: bool
    ) -> None:
        contact = setup.add_customer()
        setup.add_visit(contact, status=status, is_sandbox=is_sandbox)

        setup.run()

        assert setup.requests() == []

    def test_a_confirmed_booking_after_its_end_is_a_visit(
        self, setup: FeedbackSetup
    ) -> None:
        contact = setup.add_customer()
        setup.add_visit(contact, status=BookingStatus.CONFIRMED)

        setup.run()

        assert setup.only_request().status is FeedbackRequestStatus.SENT

    def test_feedback_off_asks_nobody(self, setup: FeedbackSetup) -> None:
        setup.save_settings(is_enabled=False)
        setup.add_visit(setup.add_customer())

        setup.run()

        assert setup.requests() == []

    def test_a_business_that_is_not_live_asks_nobody(self) -> None:
        setup = FeedbackSetup(status=BusinessStatus.PAUSED)
        setup.add_visit(setup.add_customer())

        setup.run()

        assert setup.requests() == []

    def test_the_delay_is_the_owners(self, setup: FeedbackSetup) -> None:
        setup.save_settings(delay_minutes=24 * 60)
        contact = setup.add_customer()
        setup.add_visit(contact, ended_minutes_ago=150)
        setup.add_visit(contact, ended_minutes_ago=25 * 60)

        setup.run()

        [request] = setup.requests()
        assert request.status is FeedbackRequestStatus.SENT
