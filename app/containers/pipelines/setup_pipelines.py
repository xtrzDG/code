from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.setup_orchestrators import (
    SetupOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class SetupPipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of the guided setup: progress, skipped steps, starter
    answers, the profile autosave and the milestones.
    """

    setup_orchestrators: SetupOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    get_setup_progress_pipeline = orchestrator_pipeline(
        setup_orchestrators.get_setup_progress_orchestrator
    )
    skip_setup_step_pipeline = orchestrator_pipeline(
        setup_orchestrators.skip_setup_step_orchestrator
    )
    celebrate_milestone_pipeline = orchestrator_pipeline(
        setup_orchestrators.celebrate_milestone_orchestrator
    )
    get_starter_answers_pipeline = orchestrator_pipeline(
        setup_orchestrators.get_starter_answers_orchestrator
    )
    apply_starter_answers_pipeline = orchestrator_pipeline(
        setup_orchestrators.apply_starter_answers_orchestrator
    )
    patch_profile_pipeline = orchestrator_pipeline(
        setup_orchestrators.patch_profile_orchestrator
    )
