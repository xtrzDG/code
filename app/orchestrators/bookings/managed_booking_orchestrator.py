from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.booking_manage import (
    BookingManageClaims,
    ManagedBookingAction,
    ManagedBookingRequest,
)
from app.schemas.typings.bookings.constrained_strings import BookingManageToken
from app.utilities.observability.log_context import bound_log_context


class ManagedBookingOrchestrator[OutputData](
    OrchestratorContract[ManagedBookingRequest, OutputData]
):
    """
    A guest's request through a manage link (/r/{token}): the link is
    checked first (signature and expiry; nothing is read before), then the
    request runs inside the storage scope of the business the link names
    (row-level security on Postgres), like every other request for one
    business. The same steps serve the page, its calendar file, the free
    times, the cancellation and the move.
    """

    def __init__(
        self,
        open_link: UseCaseContract[BookingManageToken, BookingManageClaims],
        act: UseCaseContract[ManagedBookingAction, OutputData],
        storage_scope: StorageScopeContract,
    ) -> None:
        self._open_link: UseCaseContract[BookingManageToken, BookingManageClaims] = (
            open_link
        )
        self._act: UseCaseContract[ManagedBookingAction, OutputData] = act
        self._storage_scope: StorageScopeContract = storage_scope

    def execute(self, input_data: ManagedBookingRequest) -> OutputData:
        claims: BookingManageClaims = self._open_link.run(input_data.token)
        with (
            bound_log_context(business_id=claims.business_id),
            self._storage_scope.scoped_to_business(claims.business_id),
        ):
            return self._act.run(
                ManagedBookingAction(
                    business_id=claims.business_id,
                    claims=claims,
                    date=input_data.date,
                    time=input_data.time,
                    client_ip_address=input_data.client_ip_address,
                )
            )
