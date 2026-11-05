"""
This release reads a booking held for its deposit and the send_payment_link
tool but stores neither name: both gates open in the next release
(docs/operations/deploys.md). Until then a held booking stays PENDING with
its deposit AWAITING, and a message keeps the payment line in its text
without naming the tool.
"""

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.conversations import ToolCallRecord
from app.schemas.exceptions.storage_errors import ClosedReleaseGateError
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    LlmToolResultJson,
)
from app.utilities.conversations.stored_tool_calls import storable_tool_calls
from app.utilities.deposits.booking_deposit_state import held_status
from app.utilities.storage.release_gates import (
    BOOKING_DEPOSITS_GATE,
    PAYMENT_LINK_TOOL_GATE,
    is_gate_open,
)
from tests.deposits.deposit_world import DepositWorld


def test_both_gates_are_closed_in_this_release() -> None:
    assert is_gate_open(BOOKING_DEPOSITS_GATE) is False
    assert is_gate_open(PAYMENT_LINK_TOOL_GATE) is False
    assert held_status() is BookingStatus.PENDING


def test_storage_refuses_pending_deposit_until_the_gate_opens() -> None:
    world = DepositWorld()
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    booking = world.big_table_booking(nino, chat)
    booking.status = BookingStatus.PENDING_DEPOSIT

    with pytest.raises(ClosedReleaseGateError, match="pending_deposit"):
        world.booking_repo.save(booking)
    assert world.booking(booking.id).status is BookingStatus.CONFIRMED


def test_a_stored_message_does_not_name_the_payment_tool_yet() -> None:
    calls = [
        ToolCallRecord(
            tool_name=AssistantToolName.CREATE_BOOKING,
            input_json=LlmToolInputJson("{}"),
            result_json=LlmToolResultJson("{}"),
        ),
        ToolCallRecord(
            tool_name=AssistantToolName.SEND_PAYMENT_LINK,
            input_json=LlmToolInputJson("{}"),
            result_json=LlmToolResultJson("{}"),
        ),
    ]

    stored = storable_tool_calls(calls)

    assert [call.tool_name for call in stored] == [AssistantToolName.CREATE_BOOKING]
