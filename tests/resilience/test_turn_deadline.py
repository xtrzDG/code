"""
A turn still running CHAT_TURN_DEADLINE_SECONDS after the customer's first
unanswered message sends one short "one moment" through the outbox, in the
customer's language; then the answer follows. It is never sent twice.
"""

from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.conversations import MessageDocument
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.assistant_texts.holding_texts import ONE_MOMENT
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.channels.outbox_reads import outbox_of
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.resilience.reply_speed_world import ReplySpeedTestbed
from tests.resilience.test_message_bursts import sent_texts

ENGLISH_HOLDING: str = LocalizedTextResolver().resolve(ONE_MOMENT, LanguageTag("en"))
# The worker picks the message up 50 ms before its deadline; the model
# thinks for 400 ms.
SECONDS_BEFORE_THE_DEADLINE: int = 19
MICROSECONDS_BEFORE_THE_DEADLINE: int = 950_000
THINKING_SECONDS: float = 0.4


def slow_turn(testbed: ReplySpeedTestbed) -> None:
    testbed.patient.thinking_seconds = THINKING_SECONDS
    testbed.clock.advance(SECONDS_BEFORE_THE_DEADLINE)
    testbed.clock.advance_microseconds(MICROSECONDS_BEFORE_THE_DEADLINE)


def holding_messages(
    testbed: ReplySpeedTestbed, business_id: BusinessId
) -> list[MessageDocument]:
    return [
        message
        for message in testbed.message_repo.list_by_business(business_id)
        if message.author is MessageAuthor.ASSISTANT
        and str(message.text) == ENGLISH_HOLDING
    ]


def test_a_slow_turn_sends_one_moment_before_the_answer() -> None:
    testbed = ReplySpeedTestbed()
    business, channel = connect_bot(testbed)
    post_update(testbed, channel, build_update(text="Is the terrace open?"))
    slow_turn(testbed)

    testbed.run_worker()

    assert sent_texts(testbed) == [ENGLISH_HOLDING, "Reply to: Is the terrace open?"]
    holding, answer = outbox_of(testbed, business.id)
    assert holding.kind is answer.kind is OutboundMessageKind.CUSTOMER_REPLY
    assert holding.conversation_id == answer.conversation_id
    [stored] = holding_messages(testbed, business.id)
    assert stored.id == holding.source_message_id
    assert stored.channel is channel.kind
    assert str(stored.language) == "en"


def test_the_holding_text_is_sent_once_when_the_turn_runs_again() -> None:
    testbed = ReplySpeedTestbed()
    business, channel = connect_bot(testbed)
    post_update(testbed, channel, build_update(text="Is the terrace open?"))
    slow_turn(testbed)
    testbed.patient.failures = [ExternalServiceError("The model timed out.")]

    testbed.run_worker()
    assert sent_texts(testbed) == [ENGLISH_HOLDING]

    # The retry starts long after the deadline: the holding text is not
    # sent again, the answer is.
    testbed.patient.thinking_seconds = 0.2
    testbed.clock.advance(3600)
    testbed.run_worker()

    assert sent_texts(testbed) == [ENGLISH_HOLDING, "Reply to: Is the terrace open?"]
    assert len(holding_messages(testbed, business.id)) == 1
    assert len(outbox_of(testbed, business.id)) == 2


def test_a_quick_turn_sends_no_holding_text() -> None:
    testbed = ReplySpeedTestbed()
    business, channel = connect_bot(testbed)
    post_update(testbed, channel, build_update(text="Hi"))
    testbed.clock.advance(3)

    testbed.run_worker()

    assert sent_texts(testbed) == ["Reply to: Hi"]
    assert holding_messages(testbed, business.id) == []


def test_the_holding_text_speaks_the_customers_language() -> None:
    testbed = ReplySpeedTestbed()
    _, channel = connect_bot(testbed)
    testbed.patient.language = LanguageTag("ka")
    post_update(testbed, channel, build_update(text="გამარჯობა, ღიაა ტერასა?"))
    slow_turn(testbed)

    testbed.run_worker()

    georgian = LocalizedTextResolver().resolve(ONE_MOMENT, LanguageTag("ka"))
    assert sent_texts(testbed)[0] == georgian
    assert georgian != ENGLISH_HOLDING


def test_no_holding_text_when_staff_own_the_conversation() -> None:
    testbed = ReplySpeedTestbed()
    business, channel = connect_bot(testbed)
    testbed.patient.is_silent = True  # the conversation is handed off
    post_update(testbed, channel, build_update(text="Hello?"))
    slow_turn(testbed)

    testbed.run_worker()

    assert ENGLISH_HOLDING not in sent_texts(testbed)
    assert holding_messages(testbed, business.id) == []
