from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.meta_connection_pipelines import (
    MetaConnectionPipelinesContainer,
)
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class MetaOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of Meta's self-serve connection: the cabinet's endpoints and
    the private reply to a comment, each in its business's scope.
    """

    meta_pipelines: MetaConnectionPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    sign_in_options_operator = pipeline_operator(
        meta_pipelines.sign_in_options_pipeline, storage_scope
    )
    start_meta_connection_operator = pipeline_operator(
        meta_pipelines.start_meta_connection_pipeline, storage_scope
    )
    complete_whatsapp_signup_operator = pipeline_operator(
        meta_pipelines.complete_whatsapp_signup_pipeline, storage_scope
    )
    list_meta_pages_operator = pipeline_operator(
        meta_pipelines.list_meta_pages_pipeline, storage_scope
    )
    connect_meta_page_operator = pipeline_operator(
        meta_pipelines.connect_meta_page_pipeline, storage_scope
    )
    set_comment_replies_operator = pipeline_operator(
        meta_pipelines.set_comment_replies_pipeline, storage_scope
    )
    # The `process_comment_trigger` job, in its event's business.
    process_comment_trigger_operator = pipeline_operator(
        meta_pipelines.process_comment_trigger_pipeline, storage_scope
    )
