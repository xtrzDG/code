from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.setup_use_cases import SetupUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.setup.setup_guide import (
    DismissSetupGuideCommand,
    MarkSetupSharedCommand,
    SetupRemindersQuery,
    SetupRemindersView,
    StartPhoneCheckCommand,
    UpdateSetupRemindersCommand,
)
from app.schemas.dto.setup.setup_progress import SetupView
from app.use_cases.setup.dismiss_setup_guide_use_case import DismissSetupGuideUseCase
from app.use_cases.setup.get_setup_reminders_use_case import GetSetupRemindersUseCase
from app.use_cases.setup.mark_setup_shared_use_case import MarkSetupSharedUseCase
from app.use_cases.setup.notice_milestones_use_case import NoticeMilestonesUseCase
from app.use_cases.setup.send_activation_nudges_use_case import (
    SendActivationNudgesUseCase,
)
from app.use_cases.setup.start_phone_check_use_case import StartPhoneCheckUseCase
from app.use_cases.setup.update_setup_reminders_use_case import (
    UpdateSetupRemindersUseCase,
)


class GuideUseCasesContainer(containers.DeclarativeContainer):
    """
    The guide after the launch: trying the assistant from a phone, the QR
    card printed, the finished guide put away, the activation reminders,
    and the two periodic jobs that notice milestones and send the nudges.
    """

    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    setup_use_cases: SetupUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    start_phone_check_use_case: Factory[
        UseCaseContract[StartPhoneCheckCommand, SetupView]
    ] = Factory(
        StartPhoneCheckUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        setup_state_repo=repositories.setup_state_repo,
        get_setup_progress=setup_use_cases.get_setup_progress_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    mark_setup_shared_use_case: Factory[
        UseCaseContract[MarkSetupSharedCommand, None]
    ] = Factory(
        MarkSetupSharedUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        setup_state_repo=repositories.setup_state_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    dismiss_setup_guide_use_case: Factory[
        UseCaseContract[DismissSetupGuideCommand, SetupView]
    ] = Factory(
        DismissSetupGuideUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        setup_state_repo=repositories.setup_state_repo,
        get_setup_progress=setup_use_cases.get_setup_progress_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_setup_reminders_use_case: Factory[
        UseCaseContract[SetupRemindersQuery, SetupRemindersView]
    ] = Factory(
        GetSetupRemindersUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        setup_state_repo=repositories.setup_state_repo,
    )
    update_setup_reminders_use_case: Factory[
        UseCaseContract[UpdateSetupRemindersCommand, SetupRemindersView]
    ] = Factory(
        UpdateSetupRemindersUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        setup_state_repo=repositories.setup_state_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    notice_milestones_use_case: Factory[UseCaseContract[JobTick, JobReport]] = Factory(
        NoticeMilestonesUseCase,
        business_repo=repositories.business_repo,
        record_activation_milestones=setup_use_cases.record_activation_milestones_use_case,
        notice_guide_progress=setup_use_cases.notice_guide_progress_use_case,
    )
    send_activation_nudges_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            SendActivationNudgesUseCase,
            business_repo=repositories.business_repo,
            channel_repo=repositories.channel_repo,
            activation_event_repo=repositories.activation_event_repo,
            setup_state_repo=repositories.setup_state_repo,
            nudge_sent_repo=repositories.nudge_sent_repo,
            owner_nudges=facilitators.owner_nudge_facilitator,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
