from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.privacy_pipelines import PrivacyPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class PrivacyOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the exports and the retention of a business's data; each
    runs inside the storage scope of its business, except the hourly purge
    of expired archives and the nightly retention purge, which look across
    every business.
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
    start_business_export_operator = pipeline_operator(
        privacy_pipelines.start_business_export_pipeline, storage_scope
    )
    list_business_exports_operator = pipeline_operator(
        privacy_pipelines.list_business_exports_pipeline, storage_scope
    )
    run_business_export_operator = pipeline_operator(
        privacy_pipelines.run_business_export_pipeline, storage_scope
    )
    download_business_export_operator = pipeline_operator(
        privacy_pipelines.download_business_export_pipeline, storage_scope
    )
    create_export_download_link_operator = pipeline_operator(
        privacy_pipelines.create_export_download_link_pipeline, storage_scope
    )
    purge_business_exports_operator = platform_pipeline_operator(
        privacy_pipelines.purge_business_exports_pipeline, storage_scope
    )
    get_privacy_settings_operator = pipeline_operator(
        privacy_pipelines.get_privacy_settings_pipeline, storage_scope
    )
    update_privacy_settings_operator = pipeline_operator(
        privacy_pipelines.update_privacy_settings_pipeline, storage_scope
    )
    retention_purge_operator = platform_pipeline_operator(
        privacy_pipelines.purge_expired_personal_data_pipeline, storage_scope
    )
    erase_copies_operator = pipeline_operator(
        privacy_pipelines.erase_processor_copies_pipeline, storage_scope
    )
