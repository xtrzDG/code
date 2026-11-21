"""
The deposit gates are open from this release: the release before it
(launch-2026-11-05) reads a booking held for its deposit and the
send_payment_link tool (docs/operations/deploys.md). A held booking is
stored PENDING_DEPOSIT with its deposit AWAITING, and a message keeps the
payment tool's call besides the payment line in its text.
"""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.conversations import ToolCallRecord
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


def test_both_gates_are_open_in_this_release() -> None:
    assert is_gate_open(BOOKING_DEPOSITS_GATE) is True
    assert is_gate_open(PAYMENT_LINK_TOOL_GATE) is True
    assert held_status() is BookingStatus.PENDING_DEPOSIT


def test_storage_keeps_pending_deposit_now_its_gate_is_open() -> None:
    world = DepositWorld()
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    booking = world.big_table_booking(nino, chat)
    booking.status = BookingStatus.PENDING_DEPOSIT

    world.booking_repo.save(booking)

    assert world.booking(booking.id).status is BookingStatus.PENDING_DEPOSIT


def test_a_stored_message_names_the_payment_tool() -> None:
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

    assert [call.tool_name for call in stored] == [
        AssistantToolName.CREATE_BOOKING,
        AssistantToolName.SEND_PAYMENT_LINK,
    ]
