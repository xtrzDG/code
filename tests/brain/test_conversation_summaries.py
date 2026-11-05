"""The summary job: queued once per active period, written after two quiet hours."""

from datetime import timedelta

import pytest

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.customer_memory.conversation_summaries import (
    ConversationSummaryWrite,
)
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSummaryText,
)
from app.utilities.memory.conversation_summary_prompt import (
    CONVERSATION_SUMMARY_SYSTEM_PROMPT,
)
from app.utilities.memory.summary_jobs import SUMMARY_IDLE_MICROSECONDS
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.memory_helpers import (
    SUMMARY_MODEL,
    build_summarizer,
    run_summary_job,
    summary_jobs,
)
from tests.brain.scripted_turns import say, scripted

TERRACE_SUMMARY: str = "Asked whether the restaurant has a terrace."


def chatting_world() -> BrainWorld:
    world = build_world(scripted(say("Yes."), say("Sure."), say("Hi!")))
    world.send("Hi, do you have a terrace?", name="Giorgi")
    return world


def only_conversation(world: BrainWorld) -> ConversationDocument:
    conversations: list[ConversationDocument] = world.conversations()
    assert len(conversations) == 1
    return conversations[0]


def now(world: BrainWorld) -> int:
    return int(world.clock.wall_clock().now_unix())


def test_a_new_conversation_queues_its_summary_two_hours_later() -> None:
    world = chatting_world()

    jobs = summary_jobs(world)

    assert len(jobs) == 1
    assert jobs[0].lane is JobLane.DEFAULT
    assert jobs[0].business_id == world.business.id
    assert jobs[0].run_at is not None
    assert int(jobs[0].run_at) == now(world) + SUMMARY_IDLE_MICROSECONDS
    assert str(only_conversation(world).id) in str(jobs[0].payload)


def test_messages_within_two_hours_queue_nothing_more() -> None:
    world = chatting_world()
    world.clock.advance(timedelta(minutes=30))

    world.send("And is it heated?")

    assert len(summary_jobs(world)) == 1


def test_a_message_after_two_quiet_hours_queues_the_next_summary() -> None:
    world = chatting_world()
    world.clock.advance(timedelta(hours=3))

    world.send("Can I book there for tonight?")

    assert len(world.conversations()) == 1
    assert len(summary_jobs(world)) == 2


def test_the_job_waits_until_the_conversation_is_quiet_for_two_hours() -> None:
    world = chatting_world()
    world.clock.advance(timedelta(minutes=90))
    world.send("And is it heated?")
    world.clock.advance(timedelta(minutes=31))
    llm = scripted(say(TERRACE_SUMMARY))

    report = run_summary_job(build_summarizer(world, llm), summary_jobs(world)[0])

    assert int(report.processed_count) == 0
    assert llm.requests == []
    moved = summary_jobs(world)[-1]
    assert moved.run_at is not None
    assert (
        int(moved.run_at)
        == int(only_conversation(world).last_message_at) + SUMMARY_IDLE_MICROSECONDS
    )


def test_the_cheap_model_writes_a_summary_of_at_most_300_characters() -> None:
    world = chatting_world()
    world.clock.advance(timedelta(hours=2))
    llm = scripted(say("Summary: " + "The guest asked about the terrace. " * 15))

    report = run_summary_job(build_summarizer(world, llm), summary_jobs(world)[0])

    assert int(report.processed_count) == 1
    request: LlmRequest = llm.requests[0]
    assert str(request.model_id) == SUMMARY_MODEL
    assert str(request.system_prompt) == CONVERSATION_SUMMARY_SYSTEM_PROMPT
    assert request.tools == []
    assert "Customer: Hi, do you have a terrace?" in str(request.transcript[0])
    conversation = only_conversation(world)
    assert conversation.summary is not None
    assert len(str(conversation.summary)) <= 300
    assert str(conversation.summary).startswith("The guest asked about the terrace.")
    assert str(conversation.summary).endswith("…")
    assert conversation.summarized_at == world.clock.wall_clock().now_unix()


def test_a_conversation_is_summarized_once_until_it_gets_new_messages() -> None:
    world = chatting_world()
    world.clock.advance(timedelta(hours=2))
    summarizer = build_summarizer(world, scripted(say(TERRACE_SUMMARY)))
    job = summary_jobs(world)[0]
    run_summary_job(summarizer, job)

    again = run_summary_job(summarizer, job)

    assert int(again.processed_count) == 0


def test_a_summary_of_an_older_state_is_not_stored() -> None:
    world = chatting_world()
    conversation = only_conversation(world)

    stored = world.conversation_repo.set_summary(
        world.business.id,
        conversation.id,
        ConversationSummaryWrite(
            summary=ConversationSummaryText(TERRACE_SUMMARY),
            written_at=world.clock.wall_clock().now_unix(),
            covers_until=type(conversation.last_message_at)(
                int(conversation.last_message_at) - 1
            ),
        ),
    )

    assert stored is None
    assert only_conversation(world).summary is None


def failing_model() -> ScriptedLlmAdapter:
    def fail(request: LlmRequest) -> ScriptedLlmTurn:
        del request
        raise ExternalServiceError("The model is down.")

    return ScriptedLlmAdapter(fail)


def test_a_failed_model_call_is_retried_then_given_up() -> None:
    world = chatting_world()
    world.clock.advance(timedelta(hours=2))
    summarizer = build_summarizer(world, failing_model())
    job = summary_jobs(world)[0]

    with pytest.raises(ExternalServiceError):
        run_summary_job(summarizer, job)

    report = run_summary_job(summarizer, job, is_final_attempt=True)
    assert int(report.processed_count) == 0
    assert only_conversation(world).summary is None


def test_owner_test_chats_queue_no_summary() -> None:
    world = build_world(scripted(say("Hello!")))

    world.send("Hi", is_sandbox=True)

    assert summary_jobs(world) == []
