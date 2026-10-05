from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.legal_pipelines import LegalPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class LegalOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the legal texts and the sub-processor list (public, no
    business) and of the notices job, which walks every business
    (platform-wide).
    """

    legal_pipelines: LegalPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    get_subprocessors_operator = pipeline_operator(
        legal_pipelines.get_subprocessors_pipeline, storage_scope
    )
    get_legal_document_operator = pipeline_operator(
        legal_pipelines.get_legal_document_pipeline, storage_scope
    )
    send_subprocessor_notices_operator = platform_pipeline_operator(
        legal_pipelines.send_subprocessor_notices_pipeline, storage_scope
    )
