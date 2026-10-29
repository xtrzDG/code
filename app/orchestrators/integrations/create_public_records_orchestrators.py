"""
The public API's creating operations: the API's request becomes the
cabinet's command (scope checked), the booking or lead use case runs
unchanged (its events then reach the webhooks), and the record comes back
in its public shape.
"""

from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.bookings import BookingResult, CreateLeadCommand, LeadView
from app.schemas.dto.operations.bookings import ManualBookingCommand
from app.schemas.dto.public_api.access import PublicBookingQuery, PublicLeadQuery
from app.schemas.dto.public_api.commands import (
    PublicBookingCommand,
    PublicLeadCommand,
)
from app.schemas.dto.public_api.records import PublicBooking, PublicLead


class CreatePublicBookingOrchestrator(
    OrchestratorContract[PublicBookingCommand, PublicBooking]
):
    def __init__(
        self,
        start_booking: UseCaseContract[PublicBookingCommand, ManualBookingCommand],
        create_booking: UseCaseContract[ManualBookingCommand, BookingResult],
        describe_booking: UseCaseContract[PublicBookingQuery, PublicBooking],
    ) -> None:
        self._start_booking: UseCaseContract[
            PublicBookingCommand, ManualBookingCommand
        ] = start_booking
        self._create_booking: UseCaseContract[ManualBookingCommand, BookingResult] = (
            create_booking
        )
        self._describe_booking: UseCaseContract[PublicBookingQuery, PublicBooking] = (
            describe_booking
        )

    def execute(self, input_data: PublicBookingCommand) -> PublicBooking:
        created = self._create_booking.run(self._start_booking.run(input_data))
        return self._describe_booking.run(
            PublicBookingQuery(
                principal=input_data.principal, booking_id=created.booking.id
            )
        )


class CreatePublicLeadOrchestrator(OrchestratorContract[PublicLeadCommand, PublicLead]):
    def __init__(
        self,
        start_lead: UseCaseContract[PublicLeadCommand, CreateLeadCommand],
        create_lead: UseCaseContract[CreateLeadCommand, LeadView],
        describe_lead: UseCaseContract[PublicLeadQuery, PublicLead],
    ) -> None:
        self._start_lead: UseCaseContract[PublicLeadCommand, CreateLeadCommand] = (
            start_lead
        )
        self._create_lead: UseCaseContract[CreateLeadCommand, LeadView] = create_lead
        self._describe_lead: UseCaseContract[PublicLeadQuery, PublicLead] = (
            describe_lead
        )

    def execute(self, input_data: PublicLeadCommand) -> PublicLead:
        created = self._create_lead.run(self._start_lead.run(input_data))
        return self._describe_lead.run(
            PublicLeadQuery(principal=input_data.principal, lead_id=created.id)
        )
