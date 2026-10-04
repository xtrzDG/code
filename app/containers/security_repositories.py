from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.security_collections_container import (
    SecurityCollectionsContainer,
)
from app.repositories.key_rotation_repository import KeyRotationRepository
from app.repositories.mfa_repositories import (
    MfaChallengeRepository,
    RecoveryCodeRepository,
    TotpFactorRepository,
)


class SecurityRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of key management (migration 1063) and two-factor
    sign-in (migration 1082). `RepositoriesContainer` extends it, so they
    are read as `repositories.key_rotation_repo`, `repositories.totp_factor_repo`…
    """

    security_collections: SecurityCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    key_rotation_repo: Singleton[KeyRotationRepository] = Singleton(
        KeyRotationRepository,
        collection=security_collections.key_rotation_collection,
    )
    totp_factor_repo: Singleton[TotpFactorRepository] = Singleton(
        TotpFactorRepository,
        collection=security_collections.totp_factor_collection,
    )
    recovery_code_repo: Singleton[RecoveryCodeRepository] = Singleton(
        RecoveryCodeRepository,
        collection=security_collections.recovery_code_collection,
    )
    mfa_challenge_repo: Singleton[MfaChallengeRepository] = Singleton(
        MfaChallengeRepository,
        collection=security_collections.mfa_challenge_collection,
    )
