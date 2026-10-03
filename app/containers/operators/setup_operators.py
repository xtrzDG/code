from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.setup_pipelines import SetupPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class SetupOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the guided setup: progress, skipped steps, starter
    answers, the profile autosave and the milestones.
    """

    setup_pipelines: SetupPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Operators run inside the storage scope of the business they serve.
    storage_scope = utilities.storage_scope

    get_setup_progress_operator = pipeline_operator(
        setup_pipelines.get_setup_progress_pipeline, storage_scope
    )
    skip_setup_step_operator = pipeline_operator(
        setup_pipelines.skip_setup_step_pipeline, storage_scope
    )
    celebrate_milestone_operator = pipeline_operator(
        setup_pipelines.celebrate_milestone_pipeline, storage_scope
    )
    get_starter_answers_operator = pipeline_operator(
        setup_pipelines.get_starter_answers_pipeline, storage_scope
    )
    apply_starter_answers_operator = pipeline_operator(
        setup_pipelines.apply_starter_answers_pipeline, storage_scope
    )
    patch_profile_operator = pipeline_operator(
        setup_pipelines.patch_profile_pipeline, storage_scope
    )
    # The guide after the launch.
    start_phone_check_operator = pipeline_operator(
        setup_pipelines.start_phone_check_pipeline, storage_scope
    )
    mark_setup_shared_operator = pipeline_operator(
        setup_pipelines.mark_setup_shared_pipeline, storage_scope
    )
    dismiss_setup_guide_operator = pipeline_operator(
        setup_pipelines.dismiss_setup_guide_pipeline, storage_scope
    )
    get_setup_reminders_operator = pipeline_operator(
        setup_pipelines.get_setup_reminders_pipeline, storage_scope
    )
    update_setup_reminders_operator = pipeline_operator(
        setup_pipelines.update_setup_reminders_pipeline, storage_scope
    )
    # Jobs over every business.
    notice_milestones_operator = platform_pipeline_operator(
        setup_pipelines.notice_milestones_pipeline, storage_scope
    )
    send_activation_nudges_operator = platform_pipeline_operator(
        setup_pipelines.send_activation_nudges_pipeline, storage_scope
    )
