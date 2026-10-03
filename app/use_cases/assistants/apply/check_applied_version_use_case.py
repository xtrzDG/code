from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.setup_repositories import AssistantApplyRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import GoLiveCheckCode
from app.schemas.constants.setup import ApplyChangesStage
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import ApplyAttentionReason
from app.schemas.dto.go_live import GoLiveReadiness, GoLiveReadinessRequest
from app.schemas.dto.setup.apply_changes import AppliedVersion
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.setup.booleans import IsApplyInProgress
from app.use_cases.assistants.apply.apply_records import move_apply
from app.utilities.analytics.product_event_drafts import launch_blocked_events
from app.utilities.setup.apply_attention import attention_from_checks

# The automatic checks are what comes next; every other gate is known now.
CHECKED_LATER: frozenset[GoLiveCheckCode] = frozenset({GoLiveCheckCode.AUTOTESTS})


class CheckAppliedVersionUseCase(UseCaseContract[AppliedVersion, IsApplyInProgress]):
    """
    Before the automatic checks play a freshly built version (they take
    minutes and model calls), look at every other launch condition: a
    missing staff contact, agreement, payment or required profile answer
    stops the apply at once with plain reasons (NEEDS_ATTENTION) instead of
    after the checks. Otherwise the apply moves on to CHECKING; True means
    the checks should start.
    """

    def __init__(
        self,
        assistant_apply_repo: AssistantApplyRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        business_repo: BusinessRepoContract,
        check_go_live_readiness: UseCaseContract[
            GoLiveReadinessRequest, GoLiveReadiness
        ],
        wall_clock: WallClock[Microseconds],
        product_events: RecordProductEventFacilitatorContract,
    ) -> None:
        self._assistant_apply_repo: AssistantApplyRepoContract = assistant_apply_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._business_repo: BusinessRepoContract = business_repo
        self._check_go_live_readiness: UseCaseContract[
            GoLiveReadinessRequest, GoLiveReadiness
        ] = check_go_live_readiness
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._product_events: RecordProductEventFacilitatorContract = product_events

    def run(self, input_data: AppliedVersion) -> IsApplyInProgress:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            input_data.business_id, input_data.assistant_version_id
        )
        if business is None or version is None:
            raise NotFoundError(
                f"Assistant version {input_data.assistant_version_id} was not found."
            )

        readiness: GoLiveReadiness = self._check_go_live_readiness.run(
            GoLiveReadinessRequest(business=business, version=version)
        )
        attention: list[ApplyAttentionReason] = attention_from_checks(
            readiness.checks, CHECKED_LATER
        )
        move_apply(
            self._assistant_apply_repo,
            business.id,
            version.id,
            ApplyChangesStage.NEEDS_ATTENTION
            if attention
            else ApplyChangesStage.CHECKING,
            self._wall_clock.now_unix(),
            attention,
        )
        self._product_events.record(*launch_blocked_events(business.id, attention))
        return attention == []
