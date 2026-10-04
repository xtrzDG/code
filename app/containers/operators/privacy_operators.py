from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.privacy_pipelines import PrivacyPipelinesContainer
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class PrivacyOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the exports of a business's data; each runs inside the
    storage scope of the business it exports.
    """

    privacy_pipelines: PrivacyPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    start_csv_export_operator = pipeline_operator(
        privacy_pipelines.start_csv_export_pipeline, storage_scope
    )
    read_csv_export_page_operator = pipeline_operator(
        privacy_pipelines.read_csv_export_page_pipeline, storage_scope
    )
