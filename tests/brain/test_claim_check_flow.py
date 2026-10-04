"""Policy and availability claims: verified, rewritten once, then handed over."""

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.conversations import MessageAuthor, ReplyGuardVerdict
from app.schemas.constants.handoffs import HandoffReason, HandoffSummaryCode
from app.schemas.constants.reply_safety import (
    ClaimTopic,
    ClaimVerdict,
    ReplyGuardReason,
)
from app.schemas.domain.conversations import MessageDocument
from app.transformers.conversations.message_view_transformer import (
    MessageViewTransformer,
)
from tests.brain.brain_orchestrators import GuardOptions
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.engine_helpers import requests_of, user_turn_text
from tests.brain.fake_claim_check import FakeClaimCheck
from tests.brain.scripted_turns import say, scripted

PARKING_FACT: tuple[str, str, str] = ("parking", "Parking", "Paid parking nearby")


def last_reply(world: BrainWorld) -> MessageDocument:
    conversation = world.conversations()[0]
    replies = [
        message
        for message in world.messages(conversation.id)
        if message.author is MessageAuthor.ASSISTANT
    ]
    return replies[-1]


def test_an_unsupported_claim_is_rewritten_once() -> None:
    check = FakeClaimCheck({"parking is free": ClaimVerdict.UNSUPPORTED})
    world = build_world(
        scripted(
            say("Parking is free for our guests."),
            say("A colleague will confirm the parking terms for you."),
        ),
        facts=[PARKING_FACT],
        guard=GuardOptions(claim_check=check),
    )

    reply = world.send("Is parking free?")

    assert reply.guard_verdict is ReplyGuardVerdict.REWRITTEN
    assert reply.text is not None
    assert reply.text.endswith("A colleague will confirm the parking terms for you.")
    note = user_turn_text(requests_of(world)[1].transcript[-1])
    assert "do not back these statements" in note
    assert "Parking is free for our guests." in note
    stored = last_reply(world)
    assert stored.guard_verdict is ReplyGuardVerdict.REWRITTEN
    assert stored.guard_reasons == [ReplyGuardReason.UNSUPPORTED_CLAIMS]
    assert [(str(item.claim), item.verdict) for item in stored.claim_findings] == [
        ("Parking is free for our guests.", ClaimVerdict.UNSUPPORTED)
    ]
    assert any(
        "Parking: Paid parking nearby" in str(text)
        for text in check.requests[0].evidence
    )
    assert world.handoffs() == []


def test_a_claim_still_unsupported_after_the_rewrite_is_handed_over() -> None:
    check = FakeClaimCheck({"dogs": ClaimVerdict.UNSUPPORTED})
    world = build_world(
        scripted(
            say("We take dogs of any size."),
            say("Yes, we accept dogs on the terrace."),
        ),
        guard=GuardOptions(claim_check=check),
    )

    reply = world.send("Can I come with my dog?")

    assert reply.guard_verdict is ReplyGuardVerdict.HANDED_OFF
    assert reply.is_handed_off is True
    assert reply.text is not None
    assert "dogs" not in reply.text
    (handoff,) = world.handoffs()
    assert handoff.reason is HandoffReason.UNKNOWN_ANSWER
    assert handoff.summary_code is HandoffSummaryCode.UNVERIFIED_VALUES
    assert handoff.flagged_values == ["Yes, we accept dogs on the terrace."]
    stored = last_reply(world)
    assert stored.guard_verdict is ReplyGuardVerdict.HANDED_OFF
    assert stored.guard_reasons == [ReplyGuardReason.UNSUPPORTED_CLAIMS]


def test_a_supported_claim_passes_and_its_check_is_stored_and_billed() -> None:
    check = FakeClaimCheck()
    world = build_world(
        scripted(say("Breakfast is included in the room price.")),
        guard=GuardOptions(claim_check=check),
    )

    reply = world.send("Is breakfast included?")

    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN
    stored = last_reply(world)
    assert stored.guard_verdict is ReplyGuardVerdict.CLEAN
    assert stored.guard_reasons == []
    assert [(item.topic, item.verdict) for item in stored.claim_findings] == [
        (ClaimTopic.POLICY, ClaimVerdict.SUPPORTED)
    ]
    verifier_tokens = [
        int(event.quantity)
        for event in world.usage_events()
        if event.kind is UsageKind.LLM_INPUT_TOKENS
    ]
    assert 1000 in verifier_tokens
    assert int(stored.cost_micro_usd) > 0


def test_questions_and_plain_answers_never_reach_the_verifier() -> None:
    check = FakeClaimCheck()
    world = build_world(
        scripted(say("Hello! Would you like free parking? What time suits you?")),
        guard=GuardOptions(claim_check=check),
    )

    world.send("Hello")

    assert check.requests == []
    assert last_reply(world).claim_findings == []


def test_with_the_check_off_claims_are_not_checked() -> None:
    world = build_world(scripted(say("Parking is free for our guests.")))

    reply = world.send("Is parking free?")

    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN
    assert last_reply(world).claim_findings == []


def test_platform_texts_carry_no_guard_verdict() -> None:
    world = build_world(scripted(say("Hello!")), contact_message_limit=1)
    world.send("Hi")

    world.send("Hi again")

    assert last_reply(world).guard_verdict is None


def test_the_conversation_card_shows_what_the_guard_did() -> None:
    check = FakeClaimCheck({"parking is free": ClaimVerdict.UNSUPPORTED})
    world = build_world(
        scripted(
            say("Parking is free for our guests."),
            say("A colleague will confirm the parking terms for you."),
        ),
        guard=GuardOptions(claim_check=check),
    )
    world.send("Is parking free?")
    conversation = world.conversations()[0]

    views = [
        MessageViewTransformer().transform(message)
        for message in world.messages(conversation.id)
    ]

    customer_view, reply_view = views
    assert customer_view.guard is None
    assert reply_view.guard is not None
    assert reply_view.guard.verdict is ReplyGuardVerdict.REWRITTEN
    assert reply_view.guard.reasons == [ReplyGuardReason.UNSUPPORTED_CLAIMS]
    assert [str(item.claim) for item in reply_view.guard.claim_findings] == [
        "Parking is free for our guests."
    ]
