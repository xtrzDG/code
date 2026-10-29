from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.idempotency import (
    IdempotencyClaim,
    IdempotencyClaimDecision,
    IdempotentRequestOutcome,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.use_cases.idempotency.claim_idempotency_key_use_case import (
    ClaimIdempotencyKeyUseCase,
)
from app.use_cases.idempotency.finish_idempotent_request_use_case import (
    FinishIdempotentRequestUseCase,
)
from app.use_cases.idempotency.purge_idempotency_keys_use_case import (
    PurgeIdempotencyKeysUseCase,
)


class IdempotencyUseCasesContainer(containers.DeclarativeContainer):
    """
    Idempotency keys of creating requests (docs/api-versioning.md): the
    claim before a request runs, its answer kept or its key released after,
    and the hourly purge of expired keys.
    """

    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    claim_idempotency_key_use_case: Factory[
        UseCaseContract[IdempotencyClaim, IdempotencyClaimDecision]
    ] = Factory(
        ClaimIdempotencyKeyUseCase,
        idempotency_key_repo=repositories.idempotency_key_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    finish_idempotent_request_use_case: Factory[
        UseCaseContract[IdempotentRequestOutcome, None]
    ] = Factory(
        FinishIdempotentRequestUseCase,
        idempotency_key_repo=repositories.idempotency_key_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # The hourly `purge_idempotency_keys` job.
    purge_idempotency_keys_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            PurgeIdempotencyKeysUseCase,
            idempotency_key_repo=repositories.idempotency_key_repo,
            audit_log_repo=repositories.audit_log_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
