from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.integrations import ApiKeyScope
from app.schemas.dto.operations.bookings import ManualBookingCommand
from app.schemas.dto.public_api.commands import PublicBookingCommand
from app.use_cases.integrations.api_key_records import require_scope


class StartPublicBookingUseCase(
    UseCaseContract[PublicBookingCommand, ManualBookingCommand]
):
    """
    A booking the API asked for, as a booking staff add by hand (the
    booking use case itself is not changed): the key's business, the key's
    owner as the actor in the audit log. Needs `bookings:write`.
    """

    def run(self, input_data: PublicBookingCommand) -> ManualBookingCommand:
        require_scope(input_data.principal, ApiKeyScope.BOOKINGS_WRITE)
        request = input_data.request
        return ManualBookingCommand(
            business_id=input_data.business_id,
            actor_id=input_data.principal.created_by,
            contact_name=request.contact_name,
            contact_phone_number=request.contact_phone_number,
            resource_id=request.resource_id,
            service_item_id=request.service_id,
            date=request.date,
            time=request.time,
            duration_minutes=request.duration_minutes,
            nights=request.nights,
            party_size=request.party_size,
            notes=request.notes,
            language=request.language,
        )
