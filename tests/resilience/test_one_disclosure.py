"""
The AI disclosure is said once. When a slow turn's "one moment" is the
assistant's first message it carries the disclosure and the reply after it
does not; a reply recorded first carries it and no "one moment" follows.
The two run on different threads and decide under the reply's lock: the
test stops one inside the lock and lets the other one ask for it, so each
order is played out for certain, not by timing.
"""

import threading
from collections.abc import Callable

from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.utilities.conversations.assistant_texts.ai_disclosure_texts import (
    AI_DISCLOSURE,
)
from app.utilities.conversations.assistant_texts.business_name_placeholder import (
    fill_business_name,
)
from app.utilities.deliveries.holding_replies import derive_holding_message_id
from tests.resilience.disclosure_world import ANSWER, WAIT_SECONDS, DisclosureWorld

HOLDING_THREAD: str = "turn-deadline"
REPLY_THREAD: str = "turn"


def disclosure(world: DisclosureWorld) -> str:
    return fill_business_name(
        world.testbed.text_resolver.resolve(
            AI_DISCLOSURE, world.business.default_language
        ),
        str(world.business.name),
    )


def start(name: str, work: Callable[[], object]) -> threading.Thread:
    thread = threading.Thread(target=work, name=name, daemon=True)
    thread.start()
    return thread


def test_a_one_moment_said_first_carries_the_disclosure_alone() -> None:
    world = DisclosureWorld()
    holding_id: MessageId = derive_holding_message_id(world.event.reply_message_id)
    world.messages.held_id = holding_id
    replies: list[AssistantReply] = []

    holding = start(HOLDING_THREAD, lambda: world.holding().run(world.event))
    # The "one moment" decided it speaks first and is being stored ...
    assert world.messages.arrived.wait(WAIT_SECONDS)
    reply = start(
        REPLY_THREAD,
        lambda: replies.append(world.recorder().run(world.reply_record())),
    )
    # ... while the reply waits for the reply's lock.
    assert world.locks.waiting(REPLY_THREAD).wait(WAIT_SECONDS)
    assert replies == []
    world.messages.gate.set()
    holding.join(WAIT_SECONDS)
    reply.join(WAIT_SECONDS)

    [answer] = replies
    assert answer.disclosure_text is None
    assert answer.text == ANSWER
    texts = world.assistant_texts()
    assert sum(text.count(disclosure(world)) for text in texts) == 1
    assert texts[0].startswith(disclosure(world))
    assert texts[1] == str(ANSWER)


def test_a_reply_recorded_first_carries_the_disclosure_and_no_one_moment_follows() -> (
    None
):
    world = DisclosureWorld()
    world.messages.held_id = world.event.reply_message_id
    replies: list[AssistantReply] = []
    held: list[MessageId | None] = []

    reply = start(
        REPLY_THREAD,
        lambda: replies.append(world.recorder().run(world.reply_record())),
    )
    # The reply decided it speaks first and is being stored ...
    assert world.messages.arrived.wait(WAIT_SECONDS)
    holding = start(
        HOLDING_THREAD, lambda: held.append(world.holding().run(world.event))
    )
    # ... while the turn deadline's "one moment" waits for the lock.
    assert world.locks.waiting(HOLDING_THREAD).wait(WAIT_SECONDS)
    assert held == []
    world.messages.gate.set()
    reply.join(WAIT_SECONDS)
    holding.join(WAIT_SECONDS)

    assert held == [None]
    [answer] = replies
    assert answer.disclosure_text is not None
    assert world.assistant_texts() == [f"{disclosure(world)}\n{ANSWER}"]


def test_without_a_holding_message_the_first_reply_discloses() -> None:
    world = DisclosureWorld()

    answer = world.recorder().run(world.reply_record())

    assert answer.text == f"{disclosure(world)}\n{ANSWER}"
