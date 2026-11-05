from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.operations.bookings import UpdateBookingCommand
from app.schemas.dto.public_api.access import PublicBookingQuery
from app.schemas.dto.public_api.commands import PublicBookingCancellation
from app.schemas.dto.public_api.records import PublicBooking


class CancelPublicBookingOrchestrator(
    OrchestratorContract[PublicBookingCancellation, PublicBooking]
):
    """
    The public API cancels a booking of the key's business: the scope is
    checked, the booking must be one the API shows (another business's or
    a test booking is not found), the cabinet's booking change cancels it
    unchanged (staff rules, the audit entry, the calendar and its webhooks
    follow), and the booking comes back in its public shape. Cancelling a
    cancelled booking again changes nothing and answers the same; one that
    already happened (completed, no-show) cannot be cancelled (409).
    """

    def __init__(
        self,
        start_cancellation: UseCaseContract[
            PublicBookingCancellation, UpdateBookingCommand
        ],
        update_booking: UseCaseContract[UpdateBookingCommand, BookingView],
        describe_booking: UseCaseContract[PublicBookingQuery, PublicBooking],
    ) -> None:
        self._start_cancellation: UseCaseContract[
            PublicBookingCancellation, UpdateBookingCommand
        ] = start_cancellation
        self._update_booking: UseCaseContract[UpdateBookingCommand, BookingView] = (
            update_booking
        )
        self._describe_booking: UseCaseContract[PublicBookingQuery, PublicBooking] = (
            describe_booking
        )

    def execute(self, input_data: PublicBookingCancellation) -> PublicBooking:
        command: UpdateBookingCommand = self._start_cancellation.run(input_data)
        query = PublicBookingQuery(
            principal=input_data.principal, booking_id=input_data.booking_id
        )
        self._describe_booking.run(query)
        self._update_booking.run(command)
        return self._describe_booking.run(query)
