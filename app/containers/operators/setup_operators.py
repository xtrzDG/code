from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.setup_pipelines import SetupPipelinesContainer
from app.containers.provider_chains import pipeline_operator
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
