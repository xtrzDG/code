from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.integrations import ApiKeyScope
from app.schemas.dto.operations.bookings import UpdateBookingCommand
from app.schemas.dto.public_api.commands import PublicBookingCancellation
from app.use_cases.integrations.api_key_records import require_scope


class StartPublicCancellationUseCase(
    UseCaseContract[PublicBookingCancellation, UpdateBookingCommand]
):
    """
    A cancellation the API asked for, as staff cancel a booking in the
    cabinet (the booking use case itself is not changed): the key's
    business, the key's owner as the actor in the audit log. Needs
    `bookings:write`.
    """

    def run(self, input_data: PublicBookingCancellation) -> UpdateBookingCommand:
        require_scope(input_data.principal, ApiKeyScope.BOOKINGS_WRITE)
        return UpdateBookingCommand(
            business_id=input_data.business_id,
            actor_id=input_data.principal.created_by,
            booking_id=input_data.booking_id,
            status=BookingStatus.CANCELLED,
        )
