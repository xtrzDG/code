from collections.abc import Callable

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.setup_repositories import (
    ActivationEventRepoContract,
    ActivationProbeRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.setup import ActivationEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.setup.setup_progress import (
    ActivationEventRecord,
    ActivationMilestoneCheck,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.setup.milestone_announcements import announce_milestone


class RecordActivationMilestonesUseCase(
    UseCaseContract[ActivationMilestoneCheck, None]
):
    """
    Notice the milestones a business reached since it was last looked at
    and store each once, with the time it really happened: going live
    (from its versions, for businesses that went live before milestones
    were recorded), the first real conversation, booking and handoff (test
    chats and automatic checks do not count). Real customers only reach a
    business that went live, so nothing is probed before that; a milestone
    already stored is never probed again. The first real conversation and
    booking, noticed within a day, are announced to the team's devices and
    Telegram chats (once: the alert names the milestone).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        activation_event_repo: ActivationEventRepoContract,
        activation_probe_repo: ActivationProbeRepoContract,
        record_activation_event: UseCaseContract[ActivationEventRecord, None],
        staff_alerts: StaffAlertFacilitatorContract,
        localized_text_resolver: LocalizedTextResolverContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._activation_event_repo: ActivationEventRepoContract = activation_event_repo
        self._activation_probe_repo: ActivationProbeRepoContract = activation_probe_repo
        self._record_activation_event: UseCaseContract[ActivationEventRecord, None] = (
            record_activation_event
        )
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ActivationMilestoneCheck) -> None:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            return

        reached: set[ActivationEventKind] = {
            event.kind
            for event in self._activation_event_repo.list_by_business(business.id)
        }
        if ActivationEventKind.WENT_LIVE not in reached:
            went_live_at: Microseconds | None = self._find_first_publish(business)
            if went_live_at is None:
                return

            self._record(business.id, ActivationEventKind.WENT_LIVE, went_live_at)

        probes: dict[
            ActivationEventKind, Callable[[BusinessId], Microseconds | None]
        ] = {
            ActivationEventKind.FIRST_CONVERSATION: (
                self._activation_probe_repo.find_first_real_conversation_at
            ),
            ActivationEventKind.FIRST_BOOKING: (
                self._activation_probe_repo.find_first_real_booking_at
            ),
            ActivationEventKind.FIRST_HANDOFF: (
                self._activation_probe_repo.find_first_real_handoff_at
            ),
        }
        for kind, probe in probes.items():
            if kind in reached:
                continue

            occurred_at: Microseconds | None = probe(business.id)
            if occurred_at is not None:
                self._record(business.id, kind, occurred_at)
                announce_milestone(
                    self._staff_alerts,
                    self._resolver,
                    business,
                    kind,
                    occurred_at,
                    self._wall_clock.now_unix(),
                )

    def _find_first_publish(self, business: BusinessDocument) -> Microseconds | None:
        if business.published_assistant_version_id is None:
            return None

        published: list[Microseconds] = [
            version.published_at
            for version in self._assistant_version_repo.list_by_business(business.id)
            if version.published_at is not None
        ]
        return min(published, default=None)

    def _record(
        self,
        business_id: BusinessId,
        kind: ActivationEventKind,
        occurred_at: Microseconds,
    ) -> None:
        self._record_activation_event.run(
            ActivationEventRecord(
                business_id=business_id, kind=kind, occurred_at=occurred_at
            )
        )
