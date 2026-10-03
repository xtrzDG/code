from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.repositories.setup_repositories import ActivationEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.setup import ActivationEventDocument
from app.schemas.dto.setup.setup_progress import ActivationEventRecord
from app.utilities.analytics.product_event_drafts import milestone_event
from app.utilities.setup.setup_keys import derive_activation_event_id


class RecordActivationEventUseCase(UseCaseContract[ActivationEventRecord, None]):
    """
    Store a milestone of a business the first time it happens (going live,
    the first test chat); later occurrences change nothing, also when two
    processes notice it at once. The milestone keeps the time it happened
    (now when the caller does not know it).
    """

    def __init__(
        self,
        activation_event_repo: ActivationEventRepoContract,
        wall_clock: WallClock[Microseconds],
        product_events: RecordProductEventFacilitatorContract,
    ) -> None:
        self._activation_event_repo: ActivationEventRepoContract = activation_event_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._product_events: RecordProductEventFacilitatorContract = product_events

    def run(self, input_data: ActivationEventRecord) -> None:
        now: Microseconds = self._wall_clock.now_unix()
        self._activation_event_repo.record_once(
            ActivationEventDocument(
                id=derive_activation_event_id(input_data.business_id, input_data.kind),
                business_id=input_data.business_id,
                kind=input_data.kind,
                occurred_at=input_data.occurred_at or now,
                created_at=now,
                updated_at=now,
            )
        )
        self._product_events.record(
            milestone_event(
                input_data.business_id, input_data.kind, input_data.occurred_at or now
            )
        )
