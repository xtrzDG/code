from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.widget_visitor_pipelines import (
    WidgetVisitorPipelinesContainer,
)
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class WidgetVisitorOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of a website chat visitor's uploads and ratings: each request names its
    business, so each runs in that business's storage scope.
    """

    widget_visitor_pipelines: WidgetVisitorPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    admit_widget_upload_operator = pipeline_operator(
        widget_visitor_pipelines.admit_widget_upload_pipeline, storage_scope
    )
    accept_widget_upload_operator = pipeline_operator(
        widget_visitor_pipelines.accept_widget_upload_pipeline, storage_scope
    )
    rate_widget_conversation_operator = pipeline_operator(
        widget_visitor_pipelines.rate_widget_conversation_pipeline, storage_scope
    )
