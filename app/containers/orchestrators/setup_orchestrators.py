from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.guide_use_cases import GuideUseCasesContainer
from app.containers.use_cases.launch_use_cases import LaunchUseCasesContainer
from app.containers.use_cases.setup_use_cases import SetupUseCasesContainer


class SetupOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the guided setup: progress, skipped steps, starter
    answers, the profile autosave and the milestones.
    """

    setup_use_cases: SetupUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    launch_use_cases: LaunchUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    guide_use_cases: GuideUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_setup_progress_orchestrator = use_case_orchestrator(
        setup_use_cases.get_setup_progress_use_case
    )
    skip_setup_step_orchestrator = use_case_orchestrator(
        setup_use_cases.skip_setup_step_use_case
    )
    celebrate_milestone_orchestrator = use_case_orchestrator(
        setup_use_cases.celebrate_milestone_use_case
    )
    get_starter_answers_orchestrator = use_case_orchestrator(
        setup_use_cases.get_starter_answers_use_case
    )
    apply_starter_answers_orchestrator = use_case_orchestrator(
        setup_use_cases.apply_starter_answers_use_case
    )
    patch_profile_orchestrator = use_case_orchestrator(
        setup_use_cases.patch_profile_use_case
    )
    # The test chat pipeline: a preview version with the owner's latest
    # edits first, the first test chat is a milestone.
    prepare_test_chat_version_orchestrator = use_case_orchestrator(
        setup_use_cases.prepare_test_chat_version_use_case
    )
    record_activation_event_orchestrator = use_case_orchestrator(
        launch_use_cases.record_activation_event_use_case
    )
    # The guide after the launch and its two periodic jobs.
    start_phone_check_orchestrator = use_case_orchestrator(
        guide_use_cases.start_phone_check_use_case
    )
    mark_setup_shared_orchestrator = use_case_orchestrator(
        guide_use_cases.mark_setup_shared_use_case
    )
    dismiss_setup_guide_orchestrator = use_case_orchestrator(
        guide_use_cases.dismiss_setup_guide_use_case
    )
    get_setup_reminders_orchestrator = use_case_orchestrator(
        guide_use_cases.get_setup_reminders_use_case
    )
    update_setup_reminders_orchestrator = use_case_orchestrator(
        guide_use_cases.update_setup_reminders_use_case
    )
    notice_milestones_orchestrator = use_case_orchestrator(
        guide_use_cases.notice_milestones_use_case
    )
    send_activation_nudges_orchestrator = use_case_orchestrator(
        guide_use_cases.send_activation_nudges_use_case
    )
