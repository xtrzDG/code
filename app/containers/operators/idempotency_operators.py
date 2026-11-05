from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.idempotency_pipelines import (
    IdempotencyPipelinesContainer,
)
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class IdempotencyOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the idempotency keys of creating requests. Their records
    are a platform collection and their inputs name no business, so they run
    unscoped, which reaches platform collections only.
    """

    idempotency_pipelines: IdempotencyPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    claim_idempotency_key_operator = pipeline_operator(
        idempotency_pipelines.claim_idempotency_key_pipeline, storage_scope
    )
    finish_idempotent_request_operator = pipeline_operator(
        idempotency_pipelines.finish_idempotent_request_pipeline, storage_scope
    )
    purge_idempotency_keys_operator = pipeline_operator(
        idempotency_pipelines.purge_idempotency_keys_pipeline, storage_scope
    )
