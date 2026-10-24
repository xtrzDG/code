"""
The conversation engine over a failing provider: the turn continues on the
fallback model with the provider-neutral transcript kept in LlmTurnDocument,
and the reply records that the fallback answered.
"""

import json

from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import LlmTurnRole, MessageAuthor
from app.schemas.domain.conversations import LlmTurnDocument, MessageDocument
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from tests.brain.brain_world import BrainWorld, build_world
from tests.resilience.failover_fakes import (
    FALLBACK_MODEL,
    PRIMARY_MODEL,
    OpenAiShapedAdapter,
    answering,
    router,
)


def world_on(primary: OpenAiShapedAdapter, fallback_text: str) -> BrainWorld:
    world = build_world(router(primary, answering(fallback_text)))
    world.version.model_id = PRIMARY_MODEL
    world.version_repo.save(world.version)
    return world


def replies(world: BrainWorld) -> list[MessageDocument]:
    [conversation] = world.conversations()
    return [
        message
        for message in world.messages(conversation.id)
        if message.direction is MessageDirection.OUTBOUND
        and message.author is MessageAuthor.ASSISTANT
    ]


def turns(world: BrainWorld) -> list[LlmTurnDocument]:
    [conversation] = world.conversations()
    return world.turns(conversation.id)


def test_assistant_turns_keep_a_provider_neutral_copy() -> None:
    primary = OpenAiShapedAdapter("Hello! How can I help?")
    world = world_on(primary, "unused")

    world.send("Hi")

    user_turn, assistant_turn = turns(world)
    assert user_turn.role is LlmTurnRole.USER
    assert user_turn.canonical_payload is None
    assert '"provider": "openai"' in str(assistant_turn.payload)
    assert assistant_turn.canonical_payload is not None
    assert json.loads(str(assistant_turn.canonical_payload)) == {
        "role": "assistant",
        "content": [{"type": "text", "text": "Hello! How can I help?"}],
    }


def test_a_failing_provider_hands_the_turn_to_the_fallback_model() -> None:
    primary = OpenAiShapedAdapter("Hello! How can I help?")
    fallback = answering("Yes, there is free parking.")
    world = build_world(router(primary, fallback))
    world.version.model_id = PRIMARY_MODEL
    world.version_repo.save(world.version)
    world.send("Hi")

    primary.is_down = True
    reply = world.send("Do you have parking?")

    assert reply.text == "Yes, there is free parking."
    assert not reply.is_handed_off
    [rerun] = fallback.requests
    assert rerun.model_id == FALLBACK_MODEL
    # The fallback reads the earlier answer as plain text, not the OpenAI
    # reasoning it could not replay.
    replayed = [json.loads(str(turn)) for turn in rerun.transcript]
    assert replayed[1] == {
        "role": "assistant",
        "content": [{"type": "text", "text": "Hello! How can I help?"}],
    }
    assert "provider" not in json.dumps(replayed)
    first, second = replies(world)
    assert (first.is_fallback_model, second.is_fallback_model) == (False, True)
    assert second.model_id == LlmModelId(FALLBACK_MODEL)
    assert first.llm_round_count == second.llm_round_count == 1
    assert first.channel is not None


def test_the_conversation_returns_to_its_model_when_the_provider_is_back() -> None:
    primary = OpenAiShapedAdapter("Welcome back.")
    world = world_on(primary, "From the fallback.")
    primary.is_down = True
    world.send("Hi")

    primary.is_down = False
    reply = world.send("Are you open today?")

    assert reply.text == "Welcome back."
    latest = primary.requests[-1]
    assert latest.model_id == PRIMARY_MODEL
    # The fallback's turn is part of the transcript the version's model reads.
    assert any("From the fallback." in str(turn) for turn in latest.transcript)
    assert [message.is_fallback_model for message in replies(world)] == [True, False]
