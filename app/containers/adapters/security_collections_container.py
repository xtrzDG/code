from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.key_rotations import KeyRotationDocument
from app.schemas.domain.mfa import (
    MfaChallengeDocument,
    RecoveryCodeDocument,
    TotpFactorDocument,
)


class SecurityCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of key management (migration 1063: the latest
    re-encryption of the stored secrets) and of two-factor sign-in
    (migration 1082: authenticators, recovery codes, second sign-in steps).
    A sibling of DocumentCollectionsContainer with the same storage factory.
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    key_rotation_collection = document_collection(
        KeyRotationDocument,
        "key_rotations",
        config,
        clients,
        utilities,
        time_provider,
    )
    totp_factor_collection = document_collection(
        TotpFactorDocument,
        "totp_factors",
        config,
        clients,
        utilities,
        time_provider,
    )
    recovery_code_collection = document_collection(
        RecoveryCodeDocument,
        "recovery_codes",
        config,
        clients,
        utilities,
        time_provider,
    )
    mfa_challenge_collection = document_collection(
        MfaChallengeDocument,
        "mfa_challenges",
        config,
        clients,
        utilities,
        time_provider,
    )
