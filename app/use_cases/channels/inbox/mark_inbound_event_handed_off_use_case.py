from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.inbox_sweep import InboundEventHandoffMark


class MarkInboundEventHandedOffUseCase(
    UseCaseContract[InboundEventHandoffMark, InboundEventDocument | None]
):
    """
    Note on an unanswered inbox event that staff were asked about, once
    (the sweeper never hands the same message off twice); None when it
    was marked already or is gone.
    """

    def __init__(
        self,
        inbound_event_repo: InboundEventRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: InboundEventHandoffMark) -> InboundEventDocument | None:
        now: Microseconds = self._wall_clock.now_unix()

        def mark(current: InboundEventDocument) -> InboundEventDocument | None:
            if current.handoff_requested_at is not None:
                return None

            current.handoff_requested_at = now
            current.updated_at = now
            return current

        return self._inbound_event_repo.update(
            input_data.business_id, input_data.event_id, mark
        )
