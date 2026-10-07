"""
After the assistant books or moves a booking in a chat, its guest gets a
written confirmation with a link to manage it. The hook belongs to the
tool layer, not to the booking use cases: bookings staff make or move in
the cabinet confirm nothing to the guest by themselves.
"""

import logging
from dataclasses import dataclass

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.bookings import BookingConfirmationChange
from app.schemas.dto.assistant_tools import AssistantToolContext, AssistantToolOutcome
from app.schemas.dto.booking_manage import (
    BookingConfirmationReceipt,
    BookingConfirmationRequest,
)

logger: logging.Logger = logging.getLogger(__name__)

CONFIRMED_CHANGES: dict[AssistantToolName, BookingConfirmationChange] = {
    AssistantToolName.CREATE_BOOKING: BookingConfirmationChange.BOOKED,
    AssistantToolName.RESCHEDULE_BOOKING: BookingConfirmationChange.MOVED,
}


@dataclass(frozen=True)
class BookingConfirmationHook:
    """Sends the confirmation of a booking a tool call made or moved."""

    send_confirmation: UseCaseContract[
        BookingConfirmationRequest, BookingConfirmationReceipt
    ]

    def after(
        self, outcome: AssistantToolOutcome, context: AssistantToolContext
    ) -> None:
        """
        Confirm a successful create_booking or reschedule_booking outside the
        owner's test chats. A failure is logged and never reaches the model:
        the booking stands, only its confirmation is missing.
        """

        change: BookingConfirmationChange | None = CONFIRMED_CHANGES.get(
            outcome.tool_name
        )
        if (
            change is None
            or outcome.confirmed_booking_id is None
            or outcome.result.is_error
            or context.is_sandbox
        ):
            return

        try:
            self.send_confirmation.run(
                BookingConfirmationRequest(
                    business_id=context.business_id,
                    booking_id=outcome.confirmed_booking_id,
                    change=change,
                    language=context.language,
                )
            )
        except Exception:
            logger.exception(
                "The confirmation of booking %s could not be sent.",
                outcome.confirmed_booking_id,
            )
