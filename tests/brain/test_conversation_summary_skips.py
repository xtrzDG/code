"""When the summary job writes nothing, and why."""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.memory_helpers import build_summarizer, run_summary_job, summary_jobs
from tests.brain.scripted_turns import say, scripted

TERRACE_SUMMARY: str = "Asked whether the restaurant has a terrace."


def quiet_world() -> BrainWorld:
    """A conversation two quiet hours after its last message."""

    world = build_world(scripted(say("Yes.")))
    world.send("Hi, do you have a terrace?", name="Giorgi")
    world.clock.advance(timedelta(hours=2))
    return world


def only_conversation(world: BrainWorld) -> ConversationDocument:
    conversations: list[ConversationDocument] = world.conversations()
    assert len(conversations) == 1
    return conversations[0]


def test_a_job_without_a_business_does_nothing() -> None:
    world = quiet_world()
    llm = scripted(say(TERRACE_SUMMARY))
    job = summary_jobs(world)[0]

    report = run_summary_job(
        build_summarizer(world, llm),
        type(job)(job.name, job.payload, None, job.run_at, job.lane),
    )

    assert int(report.processed_count) == 0
    assert llm.requests == []


def test_memory_turned_off_after_queueing_writes_no_summary() -> None:
    world = quiet_world()
    world.memory.settings_repo.change(
        world.business.id,
        lambda stored: setattr(stored, "remembers_customers", False),
        world.clock.wall_clock().now_unix(),
    )
    llm = scripted(say(TERRACE_SUMMARY))

    report = run_summary_job(build_summarizer(world, llm), summary_jobs(world)[0])

    assert int(report.processed_count) == 0
    assert llm.requests == []
    assert only_conversation(world).summary is None


def test_a_conversation_without_customer_words_is_not_summarized() -> None:
    world = quiet_world()
    world.message_repo.delete_by_conversation(
        world.business.id, only_conversation(world).id
    )
    llm = scripted(say(TERRACE_SUMMARY))

    report = run_summary_job(build_summarizer(world, llm), summary_jobs(world)[0])

    assert int(report.processed_count) == 0
    assert llm.requests == []


def test_a_message_while_the_model_writes_keeps_the_stale_summary_out() -> None:
    world = quiet_world()

    def summarize_while_the_customer_writes(request: LlmRequest) -> ScriptedLlmTurn:
        del request
        stored = only_conversation(world)
        stored.last_message_at = Microseconds(int(stored.last_message_at) + 1)
        world.conversation_repo.save(stored)
        return say(TERRACE_SUMMARY)

    report = run_summary_job(
        build_summarizer(
            world, ScriptedLlmAdapter(summarize_while_the_customer_writes)
        ),
        summary_jobs(world)[0],
    )

    assert int(report.processed_count) == 0
    assert only_conversation(world).summary is None


def test_an_unreadable_model_answer_stores_nothing() -> None:
    world = quiet_world()

    report = run_summary_job(
        build_summarizer(world, scripted(say("  "))), summary_jobs(world)[0]
    )

    assert int(report.processed_count) == 0
    assert only_conversation(world).summary is None
