from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.assistant_use_cases import AssistantUseCasesContainer
from app.containers.use_cases.pending_change_use_cases import (
    PendingChangeUseCasesContainer,
)
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.setup.apply_changes import (
    AppliedVersion,
    ApplyBuildFailure,
    ApplyChangesCommand,
    ApplyChangesQuery,
    ApplyChangesSource,
    ApplyChangesView,
    ApplyStart,
)
from app.schemas.typings.setup.booleans import IsApplyInProgress
from app.use_cases.assistants.apply.check_applied_version_use_case import (
    CheckAppliedVersionUseCase,
)
from app.use_cases.assistants.apply.describe_apply_changes_use_case import (
    DescribeApplyChangesUseCase,
)
from app.use_cases.assistants.apply.fail_apply_changes_use_case import (
    FailApplyChangesUseCase,
)
from app.use_cases.assistants.apply.get_apply_changes_use_case import (
    GetApplyChangesUseCase,
)
from app.use_cases.assistants.apply.publish_applied_version_use_case import (
    PublishAppliedVersionUseCase,
)
from app.use_cases.assistants.apply.start_apply_changes_use_case import (
    StartApplyChangesUseCase,
)


class ApplyUseCasesContainer(containers.DeclarativeContainer):
    """
    "Apply changes": registering an apply, the launch conditions checked
    before the automatic checks, publishing the version when they pass, and
    the progress the cabinet follows.
    """

    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    assistant_use_cases: AssistantUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    pending_change_use_cases: PendingChangeUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    start_apply_changes_use_case: Factory[
        UseCaseContract[ApplyChangesCommand, ApplyStart]
    ] = Factory(
        StartApplyChangesUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assistant_apply_repo=repositories.assistant_apply_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        business_profile_repo=repositories.business_profile_repo,
        collect_pending_changes=pending_change_use_cases.collect_pending_changes_use_case,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    check_applied_version_use_case: Factory[
        UseCaseContract[AppliedVersion, IsApplyInProgress]
    ] = Factory(
        CheckAppliedVersionUseCase,
        assistant_apply_repo=repositories.assistant_apply_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        business_repo=repositories.business_repo,
        check_go_live_readiness=assistant_use_cases.check_go_live_readiness_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    fail_apply_changes_use_case: Factory[UseCaseContract[ApplyBuildFailure, None]] = (
        Factory(
            FailApplyChangesUseCase,
            assistant_apply_repo=repositories.assistant_apply_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    publish_applied_version_use_case: Factory[UseCaseContract[AppliedVersion, None]] = (
        Factory(
            PublishAppliedVersionUseCase,
            assistant_apply_repo=repositories.assistant_apply_repo,
            assistant_version_repo=repositories.assistant_version_repo,
            autotest_run_repo=repositories.autotest_run_repo,
            business_repo=repositories.business_repo,
            activate_assistant_version=assistant_use_cases.activate_assistant_version_use_case,
            audit_log_repo=repositories.audit_log_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    describe_apply_changes_use_case: Factory[
        UseCaseContract[ApplyChangesSource, ApplyChangesView]
    ] = Factory(
        DescribeApplyChangesUseCase,
        assistant_apply_repo=repositories.assistant_apply_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        business_profile_repo=repositories.business_profile_repo,
        collect_pending_changes=pending_change_use_cases.collect_pending_changes_use_case,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    get_apply_changes_use_case: Factory[
        UseCaseContract[ApplyChangesQuery, ApplyChangesView]
    ] = Factory(
        GetApplyChangesUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        describe_apply_changes=describe_apply_changes_use_case,
    )
