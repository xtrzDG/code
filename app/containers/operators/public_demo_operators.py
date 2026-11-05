from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.public_demo_pipelines import (
    PublicDemoPipelinesContainer,
)
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class PublicDemoOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the landing page's sandbox demos (public, no token). A
    message runs in its demo business's storage scope; the list names no
    business and describes each demo inside that demo's own scope.
    """

    public_demo_pipelines: PublicDemoPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    list_public_demos_operator = pipeline_operator(
        public_demo_pipelines.list_public_demos_pipeline, storage_scope
    )
    public_demo_message_operator = pipeline_operator(
        public_demo_pipelines.public_demo_message_pipeline, storage_scope
    )
