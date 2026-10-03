from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.security_pipelines import SecurityPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class SecurityOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of key management: the platform admin's two routes, and the
    re-encryption job, which walks every business platform-wide.
    """

    security_pipelines: SecurityPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    get_encryption_keys_operator = pipeline_operator(
        security_pipelines.get_encryption_keys_pipeline, storage_scope
    )
    start_key_rotation_operator = pipeline_operator(
        security_pipelines.start_key_rotation_pipeline, storage_scope
    )
    rotate_encrypted_secrets_operator = platform_pipeline_operator(
        security_pipelines.rotate_encrypted_secrets_pipeline, storage_scope
    )
