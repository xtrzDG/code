"""'Apply changes' when two presses race, building fails or checks cannot start."""

from collections.abc import Callable

from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.assistants.apply_changes_orchestrator import (
    ApplyChangesOrchestrator,
)
from app.repositories.setup_repositories import AssistantApplyRepository
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.setup import ApplyAttentionCode, ApplyChangesStage
from app.schemas.domain.setup import AssistantApplyDocument
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
    RunAutotestsCommand,
)
from app.schemas.dto.assistants.assistant_views import AssistantVersionDetails
from app.schemas.dto.assistants.autotest_runs import AutotestRunPlan
from app.schemas.dto.setup.apply_changes import ApplyChangesCommand
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.assistants.apply.check_applied_version_use_case import (
    CheckAppliedVersionUseCase,
)
from app.use_cases.assistants.apply.fail_apply_changes_use_case import (
    FailApplyChangesUseCase,
)
from app.use_cases.assistants.apply.start_apply_changes_use_case import (
    StartApplyChangesUseCase,
)
from tests.assembly.international_business_seeds import seed_italian_restaurant
from tests.assembly.testbed import AssemblyTestbed
from tests.setup.apply_testbed import apply, assert_needs_attention, settle


class LateReadApplyRepository(AssistantApplyRepository):
    """Reads no apply once, as when another press stores its own meanwhile."""

    def __init__(self, stored: AssistantApplyRepository) -> None:
        self._stored: AssistantApplyRepository = stored
        self._is_first_read: bool = True

    def get_by_business(self, business_id: BusinessId) -> AssistantApplyDocument | None:
        if self._is_first_read:
            self._is_first_read = False
            return None

        return self._stored.get_by_business(business_id)

    def save(self, apply: AssistantApplyDocument) -> None:
        self._stored.save(apply)

    def insert_if_absent(self, apply: AssistantApplyDocument) -> bool:
        return self._stored.insert_if_absent(apply)

    def modify(
        self,
        business_id: BusinessId,
        change: Callable[[AssistantApplyDocument], AssistantApplyDocument | None],
    ) -> AssistantApplyDocument | None:
        return self._stored.modify(business_id, change)


class RefusingAssembly(
    UseCaseContract[AssembleAssistantVersionCommand, AssistantVersionDetails]
):
    """Building a version fails for a reason other than the profile."""

    def run(
        self, input_data: AssembleAssistantVersionCommand
    ) -> AssistantVersionDetails:
        del input_data
        raise NotFoundError("Plan voice_and_chat was not found.")


class RefusingAutotestStart(UseCaseContract[RunAutotestsCommand, AutotestRunPlan]):
    """The checks of the built version cannot start."""

    def run(self, input_data: RunAutotestsCommand) -> AutotestRunPlan:
        del input_data
        raise ConflictError("Autotests of this version are already running.")


def start_use_case(
    testbed: AssemblyTestbed,
    apply_repo: AssistantApplyRepository | None = None,
) -> StartApplyChangesUseCase:
    return StartApplyChangesUseCase(
        testbed.authorize,
        apply_repo or testbed.apply_repo,
        testbed.version_repo,
        testbed.profile_repo,
        testbed.collect_pending_changes_use_case,
        testbed.audit_repo,
        testbed.wall_clock,
    )


def orchestrator(
    testbed: AssemblyTestbed,
    *,
    assemble: UseCaseContract[AssembleAssistantVersionCommand, AssistantVersionDetails]
    | None = None,
    start_autotest_run: UseCaseContract[RunAutotestsCommand, AutotestRunPlan]
    | None = None,
) -> ApplyChangesOrchestrator:
    """The testbed's apply orchestrator with some of its steps replaced."""

    return ApplyChangesOrchestrator(
        start_apply_changes=start_use_case(testbed),
        assemble_assistant_version=assemble or testbed.assemble_use_case,
        check_applied_version=CheckAppliedVersionUseCase(
            testbed.apply_repo,
            testbed.version_repo,
            testbed.business_repo,
            testbed.check_readiness_use_case,
            testbed.wall_clock,
        ),
        start_autotest_run=start_autotest_run or testbed.start_autotest_run_use_case,
        enqueue_autotest_run=testbed.enqueue_autotest_run_use_case,
        publish_applied_version=testbed.publish_applied_use_case,
        fail_apply_changes=FailApplyChangesUseCase(
            testbed.apply_repo, testbed.wall_clock
        ),
        get_apply_changes=testbed.get_apply_use_case,
    )


def test_two_presses_at_once_start_one_apply() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    first = apply(testbed, business)
    racing = start_use_case(testbed, LateReadApplyRepository(testbed.apply_repo))

    second = racing.run(
        ApplyChangesCommand(user_id=testbed.owner_id, business_id=business.id)
    )

    assert second.is_new is False
    assert second.apply.assistant_version_id == first.assistant_version_id
    assert second.apply.stage is ApplyChangesStage.CHECKING


def test_a_version_that_cannot_be_built_needs_attention() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    testbed.advance(60)

    view = orchestrator(testbed, assemble=RefusingAssembly()).execute(
        ApplyChangesCommand(user_id=testbed.owner_id, business_id=business.id)
    )

    assert_needs_attention(view, ApplyAttentionCode.BUILD_FAILED)
    assert view.assistant_version_id is None


def test_checks_that_cannot_start_need_attention() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    testbed.advance(60)

    view = orchestrator(testbed, start_autotest_run=RefusingAutotestStart()).execute(
        ApplyChangesCommand(user_id=testbed.owner_id, business_id=business.id)
    )

    assert_needs_attention(view, ApplyAttentionCode.CHECKS_STOPPED)
    assert view.assistant_version_id is not None
    assert testbed.pending_jobs() == []


def test_a_version_published_from_advanced_counts_as_applied() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    checked = testbed.assemble(business.id, run_autotests=True)
    testbed.publish(business.id, checked.id)

    view = apply(testbed, business)

    assert view.stage is ApplyChangesStage.LIVE
    assert view.assistant_version_id == checked.id
    assert view.has_unapplied_changes is False
    assert [
        version.status for version in testbed.version_repo.list_by_business(business.id)
    ] == [AssistantVersionStatus.PUBLISHED]
