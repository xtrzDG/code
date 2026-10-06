from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.access_use_cases import AccessUseCasesContainer
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.key_rotation import (
    EncryptionKeysQuery,
    EncryptionKeysView,
    KeyRotationStarted,
    StartKeyRotationCommand,
)
from app.use_cases.admin.security.get_encryption_keys_use_case import (
    GetEncryptionKeysUseCase,
)
from app.use_cases.admin.security.rotate_encrypted_secrets_use_case import (
    RotateEncryptedSecretsUseCase,
)
from app.use_cases.admin.security.secret_resealer import SecretResealer
from app.use_cases.admin.security.start_key_rotation_use_case import (
    StartKeyRotationUseCase,
)
from app.use_cases.admin.security.totp_secret_resealer import TotpSecretResealer


class SecurityUseCasesContainer(AccessUseCasesContainer):
    """
    Key management: the platform admin's view of the key ring, starting a
    re-encryption of the stored secrets and the job that carries it out;
    and platform access (the admin team and support access, from
    AccessUseCasesContainer).
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    # The edges the base declares, shared (not redeclared), so one override
    # reaches the providers of both.
    config: ConfigContainer = AccessUseCasesContainer.config
    facilitators: FacilitatorsContainer = AccessUseCasesContainer.facilitators
    repositories: RepositoriesContainer = AccessUseCasesContainer.repositories
    time_provider: TimeProviderContainer = AccessUseCasesContainer.time_provider
    utilities: UtilitiesContainer = AccessUseCasesContainer.utilities
    platform_use_cases: PlatformUseCasesContainer = (
        AccessUseCasesContainer.platform_use_cases
    )

    get_encryption_keys_use_case: Factory[
        UseCaseContract[EncryptionKeysQuery, EncryptionKeysView]
    ] = Factory(
        GetEncryptionKeysUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        secret_rotation=adapters.secret_cipher,
        key_rotation_repo=repositories.key_rotation_repo,
    )
    start_key_rotation_use_case: Factory[
        UseCaseContract[StartKeyRotationCommand, KeyRotationStarted]
    ] = Factory(
        StartKeyRotationUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        secret_rotation=adapters.secret_cipher,
        key_rotation_repo=repositories.key_rotation_repo,
        job_queue=facilitators.job_queue_facilitator,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        step_up=utilities.step_up_guard,
    )
    secret_resealer: Factory[SecretResealer] = Factory(
        SecretResealer,
        channel_repo=repositories.channel_repo,
        calendar_connection_repo=repositories.calendar_connection_repo,
        secret_cipher=adapters.secret_cipher,
        secret_rotation=adapters.secret_cipher,
        telegram_client=clients.telegram_bot_client,
        app_settings=config.app_settings,
        calendar_link_repo=repositories.resource_calendar_link_repo,
    )
    totp_secret_resealer: Factory[TotpSecretResealer] = Factory(
        TotpSecretResealer,
        totp_factor_repo=repositories.totp_factor_repo,
        totp_secret_cipher=adapters.totp_secret_cipher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    rotate_encrypted_secrets_use_case: Factory[
        UseCaseContract[QueuedJobInput, JobReport]
    ] = Factory(
        RotateEncryptedSecretsUseCase,
        business_repo=repositories.business_repo,
        key_rotation_repo=repositories.key_rotation_repo,
        secret_rotation=adapters.secret_cipher,
        resealer=secret_resealer,
        wall_clock=time_provider.microsecond_wall_clock,
        totp_resealer=totp_secret_resealer,
    )
