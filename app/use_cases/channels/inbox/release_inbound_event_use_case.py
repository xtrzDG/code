from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deliveries import InboundEventStatus
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.deliveries import InboundFailure
from app.utilities.deliveries.inbound_claims import is_inbound_event_finished


class ReleaseInboundEventUseCase(
    UseCaseContract[InboundFailure, InboundEventDocument | None]
):
    """
    Processing of an inbox event failed. A final failure (the business is
    not live, the message is invalid, or the job's last attempt) marks it
    FAILED with the reason; any other failure only gives the event up with
    the reason, so the job's next attempt may take it at once.
    """

    def __init__(
        self,
        inbound_event_repo: InboundEventRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: InboundFailure) -> InboundEventDocument | None:
        now: Microseconds = self._wall_clock.now_unix()

        def release(current: InboundEventDocument) -> InboundEventDocument | None:
            if is_inbound_event_finished(current):
                return None

            if input_data.is_final:
                current.status = InboundEventStatus.FAILED
                current.processed_at = now

            current.lease_until = None
            current.last_error = input_data.error
            current.updated_at = now
            return current

        return self._inbound_event_repo.update(
            input_data.business_id, input_data.event_id, release
        )
