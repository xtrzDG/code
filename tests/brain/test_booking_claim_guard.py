"""
A reply says a booking is made, confirmed, moved or cancelled only in a
turn where a booking tool succeeded (AI-08); otherwise the guard asks for
one rewrite and then hands the conversation to a colleague.
"""

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import MessageAuthor, ReplyGuardVerdict
from app.schemas.constants.reply_safety import (
    ClaimTopic,
    ClaimVerdict,
    ReplyGuardReason,
)
from app.schemas.domain.conversations import ToolCallRecord
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    LlmToolResultJson,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.reply_guard.booking_claims import find_unbacked_booking_claims
from tests.brain.brain_world import build_world
from tests.brain.engine_helpers import requests_of, user_turn_text
from tests.brain.scripted_turns import call_tool, say, scripted

CREATE_INPUT: str = (
    '{"name":"Нино","phone":null,"resource_type":"table",'
    '"date":"2026-10-02","time":"19:30","party_size":4,'
    '"duration_minutes":null,"nights":null,"notes":null}'
)


def tool_record(name: AssistantToolName, *, is_error: bool) -> ToolCallRecord:
    return ToolCallRecord(
        tool_name=name,
        input_json=LlmToolInputJson("{}"),
        result_json=LlmToolResultJson("{}"),
        is_error=is_error,
    )


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("Done! You are booked for Thursday at 19:00.", "en"),
        ("Your booking for Friday has been cancelled.", "en"),
        ("I have moved your booking to 20:00.", "en"),
        ("Fatto! La prenotazione è confermata per giovedì.", "it"),
        ("Ho spostato la prenotazione alle 20.", "it"),
        ("Готово, бронь отменена.", "ru"),
        ("ჯავშანი დადასტურებულია.", "ka"),
        ("C'est fait, votre table est réservée.", "fr"),
    ],
)
def test_a_done_booking_without_a_tool_is_a_claim(text: str, language: str) -> None:
    assert find_unbacked_booking_claims(text, [LanguageTag(language)], []) != []


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("Shall I book Thursday at 19:00 for you?", "en"),
        ("Cancellation is free up to 24 hours before.", "en"),
        ("When the booking is confirmed, we will text you.", "en"),
        ("Friday is fully booked, but Saturday is free.", "en"),
        ("Vuole che prenoti giovedì alle 19?", "it"),
        ("Se la prenotazione è confermata, le scriviamo.", "it"),
        ("Бронь не отменена, она в силе.", "ru"),
    ],
)
def test_offers_rules_plans_and_negations_are_not_claims(
    text: str, language: str
) -> None:
    assert find_unbacked_booking_claims(text, [LanguageTag(language)], []) == []


def test_a_successful_booking_tool_backs_the_claim() -> None:
    text = "Done! You are booked for Thursday."
    english = [LanguageTag("en")]

    for tool in (
        AssistantToolName.CREATE_BOOKING,
        AssistantToolName.RESCHEDULE_BOOKING,
        AssistantToolName.CANCEL_BOOKING,
        AssistantToolName.LIST_MY_BOOKINGS,
    ):
        backed = [tool_record(tool, is_error=False)]
        assert find_unbacked_booking_claims(text, english, backed) == []

    failed = [tool_record(AssistantToolName.CREATE_BOOKING, is_error=True)]
    other = [tool_record(AssistantToolName.CHECK_AVAILABILITY, is_error=False)]
    assert find_unbacked_booking_claims(text, english, failed) == [
        "You are booked for Thursday."
    ]
    assert find_unbacked_booking_claims(text, english, other) != []


def test_a_false_confirmation_is_rewritten_once() -> None:
    world = build_world(
        scripted(
            say("Done! You are booked for Friday at 19:30."),
            say("Friday at 19:30 is free. Shall I book it under your name?"),
        )
    )

    reply = world.send("A table for Friday at 19:30, please", name="Nino")

    assert reply.guard_verdict is ReplyGuardVerdict.REWRITTEN
    assert reply.created_booking_ids == []
    note = user_turn_text(requests_of(world)[1].transcript[-1])
    assert "No booking tool succeeded in this turn" in note
    assert "You are booked for Friday at 19:30." in note
    stored = world.messages(reply.conversation_id)[-1]
    assert stored.author is MessageAuthor.ASSISTANT
    assert stored.guard_reasons == [ReplyGuardReason.UNSUPPORTED_CLAIMS]
    assert [(f.topic, f.verdict) for f in stored.claim_findings] == [
        (ClaimTopic.AVAILABILITY, ClaimVerdict.UNSUPPORTED)
    ]


def test_a_confirmation_repeated_after_the_rewrite_goes_to_a_colleague() -> None:
    world = build_world(
        scripted(
            say("Your booking is confirmed."),
            say("All set: your booking is confirmed for Friday."),
        )
    )

    reply = world.send("Is my table for Friday booked?", name="Nino")

    assert reply.guard_verdict is ReplyGuardVerdict.HANDED_OFF
    assert reply.is_handed_off is True
    assert reply.text is not None
    assert "confirmed" not in reply.text
    assert len(world.handoffs()) == 1


def test_a_confirmation_after_create_booking_passes() -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.CREATE_BOOKING, CREATE_INPUT),
            say("Done! You are booked for 2 October at 19:30, Нино."),
        )
    )

    reply = world.send("A table for 4 on 2 October at 19:30", name="Нино")

    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN
    assert len(reply.created_booking_ids) == 1


@pytest.mark.parametrize(
    ("text", "language", "earlier", "is_backed"),
    [
        ("Your table is confirmed.", "en", AssistantToolName.CREATE_BOOKING, True),
        ("La prenotazione è confermata.", "it", AssistantToolName.CREATE_BOOKING, True),
        ("Your table is confirmed.", "en", AssistantToolName.LIST_MY_BOOKINGS, True),
        ("Your booking is cancelled.", "en", AssistantToolName.CREATE_BOOKING, False),
        ("Your booking is cancelled.", "en", AssistantToolName.CANCEL_BOOKING, True),
        (
            "Ho annullato la prenotazione.",
            "it",
            AssistantToolName.CREATE_BOOKING,
            False,
        ),
        ("I have moved your booking.", "en", AssistantToolName.CREATE_BOOKING, False),
        (
            "Бронь перенесена на 20:00.",
            "ru",
            AssistantToolName.RESCHEDULE_BOOKING,
            True,
        ),
        (
            "Your new table is booked and the old one is cancelled.",
            "en",
            AssistantToolName.CREATE_BOOKING,
            False,
        ),
    ],
)
def test_an_earlier_tool_call_backs_a_repeated_claim_of_its_kind_only(
    text: str, language: str, earlier: AssistantToolName, is_backed: bool
) -> None:
    claims = find_unbacked_booking_claims(
        text, [LanguageTag(language)], [], [tool_record(earlier, is_error=False)]
    )
    failed = find_unbacked_booking_claims(
        text, [LanguageTag(language)], [], [tool_record(earlier, is_error=True)]
    )

    assert (claims == []) is is_backed
    assert failed != []


def test_a_later_reply_may_repeat_the_booking_an_earlier_turn_made() -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.CREATE_BOOKING, CREATE_INPUT),
            say("Done! You are booked for 2 October at 19:30, Нино."),
            say("You're welcome, Нино! Your booking is confirmed. See you!"),
        )
    )
    world.send("A table for 4 on 2 October at 19:30", name="Нино")

    reply = world.send("Thank you!", name="Нино")

    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN
    assert len(requests_of(world)) == 3


def test_an_earlier_booking_never_backs_a_cancellation_the_turn_did_not_make() -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.CREATE_BOOKING, CREATE_INPUT),
            say("Done! You are booked for 2 October at 19:30, Нино."),
            say("Your booking has been cancelled."),
            say("I can pass the cancellation to a colleague right away."),
        )
    )
    world.send("A table for 4 on 2 October at 19:30", name="Нино")

    reply = world.send("Please cancel it.", name="Нино")

    assert reply.guard_verdict is ReplyGuardVerdict.REWRITTEN
    note = user_turn_text(requests_of(world)[3].transcript[-1])
    assert "Your booking has been cancelled." in note
