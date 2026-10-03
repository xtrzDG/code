from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.repositories.setup_repositories import SetupStateRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import SetupStateDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.setup.setup_progress import (
    SetupQuery,
    SetupView,
    SkipSetupStepCommand,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.analytics.product_event_drafts import tunnel_step_skipped_events
from app.utilities.setup.guide_steps import AFTER_LAUNCH_STEPS, SKIPPABLE_STEPS


class SkipSetupStepUseCase(UseCaseContract[SkipSetupStepCommand, SetupView]):
    """
    The owner skips an optional setup step (what they offer, channels,
    trying the assistant, and every step of the guide after the launch) or
    brings it back; the steps the assistant cannot work without are never
    skipped. A step after the launch is remembered apart (see
    `SetupStateDocument`). Returns the setup as it stands then.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        setup_state_repo: SetupStateRepoContract,
        get_setup_progress: UseCaseContract[SetupQuery, SetupView],
        wall_clock: WallClock[Microseconds],
        product_events: RecordProductEventFacilitatorContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._setup_state_repo: SetupStateRepoContract = setup_state_repo
        self._get_setup_progress: UseCaseContract[SetupQuery, SetupView] = (
            get_setup_progress
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._product_events: RecordProductEventFacilitatorContract = product_events

    def run(self, input_data: SkipSetupStepCommand) -> SetupView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        if input_data.step not in SKIPPABLE_STEPS:
            raise ValidationFailedError(
                f"Step {input_data.step.value} is needed to go live and cannot be "
                "skipped."
            )

        is_after_launch: bool = input_data.step in AFTER_LAUNCH_STEPS

        def toggle(state: SetupStateDocument) -> None:
            stored = (
                state.skipped_after_launch if is_after_launch else state.skipped_steps
            )
            skipped = [step for step in stored if step != input_data.step]
            if input_data.is_skipped:
                skipped.append(input_data.step)

            if is_after_launch:
                state.skipped_after_launch = skipped
            else:
                state.skipped_steps = skipped

        self._setup_state_repo.change(business.id, toggle, self._wall_clock.now_unix())
        self._product_events.record(
            *tunnel_step_skipped_events(
                input_data.user_id, business.id, input_data.step, input_data.is_skipped
            )
        )
        return self._get_setup_progress.run(
            SetupQuery(user_id=input_data.user_id, business_id=business.id)
        )
