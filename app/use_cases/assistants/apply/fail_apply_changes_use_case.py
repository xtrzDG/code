from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.setup_repositories import AssistantApplyRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.setup import ApplyChangesStage
from app.schemas.domain.setup import ApplyAttentionReason
from app.schemas.dto.setup.apply_changes import ApplyBuildFailure
from app.use_cases.assistants.apply.apply_records import move_apply
from app.utilities.analytics.product_event_drafts import launch_blocked_events


class FailApplyChangesUseCase(UseCaseContract[ApplyBuildFailure, None]):
    """
    An apply that could not go on (the version could not be built, or its
    checks could not start) needs the owner's attention, with the reason.
    """

    def __init__(
        self,
        assistant_apply_repo: AssistantApplyRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        product_events: RecordProductEventFacilitatorContract,
    ) -> None:
        self._assistant_apply_repo: AssistantApplyRepoContract = assistant_apply_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._product_events: RecordProductEventFacilitatorContract = product_events

    def run(self, input_data: ApplyBuildFailure) -> None:
        reasons: list[ApplyAttentionReason] = [
            ApplyAttentionReason(
                code=input_data.code,
                details=[] if input_data.detail is None else [input_data.detail],
            )
        ]
        move_apply(
            self._assistant_apply_repo,
            self._live_events,
            input_data.business_id,
            input_data.assistant_version_id,
            ApplyChangesStage.NEEDS_ATTENTION,
            self._wall_clock.now_unix(),
            reasons,
        )
        self._product_events.record(
            *launch_blocked_events(input_data.business_id, reasons)
        )
