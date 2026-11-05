from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.autotest_case_repositories import (
    AutotestCaseRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.assistants import AutotestScenarioResult
from app.schemas.domain.autotest_cases import AutotestCaseDocument, OwnerCheckProbe
from app.schemas.dto.assistants.autotest_cases import (
    OwnerCheckOutcomeView,
    OwnerCheckProbeOutcome,
)
from app.use_cases.shared.owner_check_outcomes import first_answer, to_probe_view


class RecordOwnerCheckProbeUseCase(
    UseCaseContract[OwnerCheckProbeOutcome, OwnerCheckOutcomeView]
):
    """
    Keep how "Check now" went on the check (`last_probe`) and say it in the
    owner's words. The check itself does not change: a probe that passed
    on the live version after the check's last change counts as checked
    against it (the check leaves the changes "Apply changes" lists), one
    that failed keeps it there. Kept in one step and only when nobody
    changed or removed the check while it was asked, since the answer
    belongs to the question as it was; the outcome is returned either way.
    Open cabinets read the business's changes again.
    """

    def __init__(
        self,
        autotest_case_repo: AutotestCaseRepoContract,
        localized_text_resolver: LocalizedTextResolverContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._autotest_case_repo: AutotestCaseRepoContract = autotest_case_repo
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: OwnerCheckProbeOutcome) -> OwnerCheckOutcomeView:
        case: AutotestCaseDocument = input_data.start.case
        result: AutotestScenarioResult = input_data.result
        probe = OwnerCheckProbe(
            assistant_version_id=input_data.start.scenario_run.version.id,
            outcome=result.outcome,
            check_codes=list(result.check_codes),
            answer=first_answer(result.transcript),
            judge_notes=list(result.judge_notes),
            conversation_id=result.conversation_id,
            answer_message_id=result.answer_message_id,
            checked_at=self._wall_clock.now_unix(),
        )

        def keep(stored: AutotestCaseDocument) -> AutotestCaseDocument | None:
            if int(stored.updated_at) != int(case.updated_at):
                return None

            stored.last_probe = probe
            return stored

        if self._autotest_case_repo.modify(case.business_id, case.id, keep):
            self._live_events.publish(
                case.business_id,
                LiveEventKind.ASSISTANT_APPLY,
                (input_data.start.scenario_run.version.id,),
            )

        return to_probe_view(self._resolver, case, probe, input_data.start.language)
