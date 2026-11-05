"""
The tool layer confirms what the assistant booked or moved to the guest in
writing; nothing else triggers it, and its failure never reaches the model.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import pytest

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.bookings import BookingConfirmationChange
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolInvocation,
    AssistantToolOutcome,
)
from app.schemas.dto.booking_manage import (
    BookingConfirmationReceipt,
    BookingConfirmationRequest,
)
from app.schemas.dto.conversations import LlmToolCall
from app.schemas.typings.bookings.booleans import IsBookingConfirmationQueued
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import LlmToolCallId, LlmToolInputJson
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from tests.brain.brain_business_seed import seed_business
from tests.brain.brain_repositories import build_brain_repositories
from tests.brain.brain_tools import BrainTools, build_brain_tools
from tests.brain.business_setups import GEORGIA, default_menu
from tests.brain.manual_clock import ManualClock
from tests.brain.tool_runner_helpers import BOOKING_ARGUMENTS


@dataclass
class RecordingConfirmations(
    UseCaseContract[BookingConfirmationRequest, BookingConfirmationReceipt]
):
    requests: list[BookingConfirmationRequest] = field(
        default_factory=list[BookingConfirmationRequest]
    )
    failure: Exception | None = None

    def run(self, input_data: BookingConfirmationRequest) -> BookingConfirmationReceipt:
        self.requests.append(input_data)
        if self.failure is not None:
            raise self.failure

        return BookingConfirmationReceipt(is_queued=IsBookingConfirmationQueued(True))


@dataclass(frozen=True)
class ToolWorld:
    tools: BrainTools
    confirmations: RecordingConfirmations
    context: AssistantToolContext

    def run(
        self,
        tool_name: AssistantToolName,
        arguments: dict[str, Any],
        **context_changes: Any,
    ) -> AssistantToolOutcome:
        return self.tools.run_tool.run(
            AssistantToolInvocation(
                context=self.context.model_copy(update=context_changes),
                call=LlmToolCall(
                    call_id=LlmToolCallId("call_1"),
                    tool_name=tool_name,
                    input_json=LlmToolInputJson(json.dumps(arguments)),
                ),
            )
        )


def tool_world(failure: Exception | None = None) -> ToolWorld:
    clock = ManualClock()
    repos = build_brain_repositories()
    business = seed_business(
        repos, GEORGIA, tools=None, facts=None, hours=None, is_published=True
    ).business
    confirmations = RecordingConfirmations(failure=failure)
    tools = build_brain_tools(
        repos,
        business,
        default_menu(GEORGIA),
        clock.wall_clock(),
        send_booking_confirmation=confirmations,
    )
    context = AssistantToolContext(
        business_id=business.id,
        business_country_code=business.country_code,
        contact_id=ContactId(),
        contact_phone_number=E164PhoneNumber("+995577000111"),
        verified_phone_number=E164PhoneNumber("+995577000111"),
        conversation_id=ConversationId(),
        channel=ChannelKind.TELEGRAM,
        language=LanguageTag("ru"),
        available_tools=list(AssistantToolName),
    )
    return ToolWorld(tools=tools, confirmations=confirmations, context=context)


def test_a_booking_the_assistant_makes_is_confirmed_in_the_guests_language() -> None:
    world = tool_world()

    outcome = world.run(AssistantToolName.CREATE_BOOKING, BOOKING_ARGUMENTS)

    assert outcome.result.is_error is False
    assert outcome.booking_id is not None
    assert outcome.confirmed_booking_id == outcome.booking_id
    assert world.confirmations.requests == [
        BookingConfirmationRequest(
            business_id=world.context.business_id,
            booking_id=outcome.booking_id,
            change=BookingConfirmationChange.BOOKED,
            language=LanguageTag("ru"),
        )
    ]


def test_a_move_is_confirmed_as_a_move() -> None:
    world = tool_world()
    booked = world.run(AssistantToolName.CREATE_BOOKING, BOOKING_ARGUMENTS)
    assert booked.booking_id is not None

    moved = world.run(
        AssistantToolName.RESCHEDULE_BOOKING,
        {
            "booking_id": str(booked.booking_id),
            "phone": None,
            "old_date": None,
            "new_date": "2026-10-03",
            "new_time": "20:00",
        },
    )

    assert moved.result.is_error is False, moved.result.result_json
    assert moved.booking_id is None
    assert moved.confirmed_booking_id == booked.booking_id
    assert [request.change for request in world.confirmations.requests] == [
        BookingConfirmationChange.BOOKED,
        BookingConfirmationChange.MOVED,
    ]


def test_refusals_cancellations_and_test_chats_confirm_nothing() -> None:
    world = tool_world()
    world.tools.bookings.is_slot_taken = True
    refused = world.run(AssistantToolName.CREATE_BOOKING, BOOKING_ARGUMENTS)
    assert refused.result.is_error is True

    world.tools.bookings.is_slot_taken = False
    sandboxed = world.run(
        AssistantToolName.CREATE_BOOKING, BOOKING_ARGUMENTS, is_sandbox=True
    )
    assert sandboxed.result.is_error is False
    cancelled = world.run(
        AssistantToolName.CANCEL_BOOKING,
        {"booking_id": str(sandboxed.booking_id), "phone": None, "date": None},
    )
    assert cancelled.result.is_error is False, cancelled.result.result_json
    assert cancelled.confirmed_booking_id is None

    assert world.confirmations.requests == []


def test_a_failed_confirmation_leaves_the_booking_and_the_answer(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = tool_world(failure=RuntimeError("outbox unavailable"))

    with caplog.at_level(logging.ERROR):
        outcome = world.run(AssistantToolName.CREATE_BOOKING, BOOKING_ARGUMENTS)

    assert outcome.result.is_error is False
    assert json.loads(outcome.result.result_json)["status"] == "confirmed"
    assert len(world.confirmations.requests) == 1
    assert "could not be sent" in caplog.text
    assert "Nino" not in caplog.text
