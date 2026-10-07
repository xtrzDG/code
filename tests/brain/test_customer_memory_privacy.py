"""
The memory stays with its customer and business: an erased customer starts
from zero, another business never sees it, and it lives in the user turn so
the conversation's prompt prefix stays byte for byte the same.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.conversations import LlmRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSummaryText,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.utilities.privacy.erased_conversations import ERASED_CHANNEL_USER_ID_PREFIX
from tests.brain.brain_world import CUSTOMER_PHONE, BrainWorld, build_world
from tests.brain.engine_helpers import requests_of, user_turn_text
from tests.brain.memory_helpers import (
    add_booking,
    build_summarizer,
    only_contact,
    run_summary_job,
    summary_jobs,
)
from tests.brain.scripted_turns import say, scripted

SATURDAY_EVENING: datetime = datetime(
    2026, 10, 3, 20, 0, tzinfo=ZoneInfo("Asia/Tbilisi")
)
SUMMARY: str = "Booked a table for 4 on Saturday at 20:00."


def summarized_customer(world: BrainWorld) -> ContactDocument:
    """A customer whose first conversation is summarized and who has a booking."""

    world.send("A table for 4 on Saturday at 20:00, please", name="Giorgi")
    contact = only_contact(world)
    add_booking(world, contact, SATURDAY_EVENING)
    world.clock.advance(timedelta(hours=2))
    run_summary_job(
        build_summarizer(world, scripted(say(SUMMARY))), summary_jobs(world)[0]
    )
    assert world.conversations()[0].summary is not None
    return contact


def erase(world: BrainWorld, contact: ContactDocument) -> None:
    """What the owner's erasure leaves (DeleteContactDataUseCase)."""

    for conversation in world.conversations():
        conversation.channel_user_id = ChannelUserId(
            f"{ERASED_CHANNEL_USER_ID_PREFIX}{conversation.id}"
        )
        conversation.status = ConversationStatus.CLOSED
        conversation.summary = None
        conversation.summarized_at = None
        world.conversation_repo.save(conversation)

    world.contact_repo.save(
        ContactDocument(
            id=contact.id,
            business_id=world.business.id,
            erased_at=world.clock.wall_clock().now_unix(),
            created_at=contact.created_at,
        )
    )


def first_turn(request: LlmRequest) -> str:
    return user_turn_text(request.transcript[0])


def test_an_erased_customer_gets_no_memory() -> None:
    world = build_world(scripted(say("Booked."), say("Hello! How can I help?")))
    contact = summarized_customer(world)
    erase(world, contact)
    world.clock.advance(timedelta(days=1))

    world.send("Hi, what time is my booking?")

    turn: str = first_turn(requests_of(world)[-1])
    assert "Returning customer" not in turn
    assert "Table 4" not in turn
    assert SUMMARY not in turn
    assert len(world.contacts()) == 2


def test_no_summary_is_written_for_an_erased_customer() -> None:
    world = build_world(scripted(say("Booked.")))
    world.send("A table for 4 on Saturday at 20:00, please", name="Giorgi")
    erase(world, only_contact(world))
    world.clock.advance(timedelta(hours=2))
    llm = scripted(say(SUMMARY))

    report = run_summary_job(build_summarizer(world, llm), summary_jobs(world)[0])

    assert int(report.processed_count) == 0
    assert llm.requests == []
    assert world.conversations()[0].summary is None


def other_business(world: BrainWorld) -> BusinessDocument:
    business = world.business.model_copy(update={"id": BusinessId()})
    world.business_repo.save(business)
    return business


def test_memory_never_crosses_businesses() -> None:
    world = build_world(scripted(say("Hello!")))
    elsewhere = other_business(world)
    # The same person, known to another business of the platform.
    neighbour = ContactDocument(
        business_id=elsewhere.id,
        phone_number=CUSTOMER_PHONE,
        verified_phone_number=CUSTOMER_PHONE,
    )
    world.contact_repo.save(neighbour)
    world.conversation_repo.save(
        ConversationDocument(
            business_id=elsewhere.id,
            contact_id=neighbour.id,
            assistant_version_id=world.version.id,
            channel=ChannelKind.WHATSAPP,
            channel_user_id=ChannelUserId("995555123456"),
            last_message_at=world.clock.wall_clock().now_unix(),
            summary=ConversationSummaryText("Asked about wine pairings."),
        )
    )
    add_booking(world, neighbour, SATURDAY_EVENING)

    world.send("Hi, what time is my booking?", name="Giorgi")

    turn: str = first_turn(requests_of(world)[-1])
    assert "Returning customer" not in turn
    assert "wine pairings" not in turn
    assert "Table 4" not in turn


def test_the_prompt_prefix_stays_byte_stable() -> None:
    world = build_world(
        scripted(say("Booked."), say("Welcome back!"), say("At 20:00."), say("Bye!"))
    )
    summarized_customer(world)
    world.clock.advance(timedelta(days=1))

    world.send("Hello again!")
    world.send("What time was it?")

    requests: list[LlmRequest] = requests_of(world)
    first_conversation, opening, follow_up = requests[0], requests[-2], requests[-1]
    # The memory is in the returning conversation's first user turn ...
    assert "Returning customer" in first_turn(opening)
    # ... never in the instruction or the tools, which stay as they were.
    assert opening.system_prompt == first_conversation.system_prompt
    assert opening.tools == first_conversation.tools
    assert follow_up.system_prompt == opening.system_prompt
    assert follow_up.tools == opening.tools
    # Every earlier turn is resent byte for byte: only turns are appended.
    assert follow_up.transcript[: len(opening.transcript)] == opening.transcript
    assert "Returning customer" not in user_turn_text(follow_up.transcript[-1])
