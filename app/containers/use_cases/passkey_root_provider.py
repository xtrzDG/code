from dependency_injector.providers import Factory, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.passkeys.passkey_dependencies import PasskeyDependencies
from app.containers.passkeys.passkey_root import PasskeyRoot
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.utilities import UtilitiesContainer


def passkey_root_provider(
    *,
    adapters: AdaptersContainer,
    config: ConfigContainer,
    facilitators: FacilitatorsContainer,
    registries: RegistriesContainer,
    repositories: RepositoriesContainer,
    time_provider: TimeProviderContainer,
    transformers: TransformersContainer,
    utilities: UtilitiesContainer,
) -> Singleton[PasskeyRoot]:
    """
    The passkey context's one root (W20, migration 1201), its dependencies
    taken from the graph: the single seam between the providers and the
    typed root (app/containers/passkeys/, ADR 0010; a missing or misspelt
    field fails test_every_provider_of_the_container_resolves).
    """

    return Singleton(
        PasskeyRoot,
        dependencies=Factory(
            PasskeyDependencies,
            passkey_repo=repositories.passkey_repo,
            challenge_repo=repositories.passkey_challenge_repo,
            user_repo=repositories.user_repo,
            user_session_repo=repositories.user_session_repo,
            mfa_challenge_repo=repositories.mfa_challenge_repo,
            totp_factor_repo=repositories.totp_factor_repo,
            recovery_code_repo=repositories.recovery_code_repo,
            audit_log_repo=repositories.audit_log_repo,
            ceremony=adapters.passkey_ceremony,
            session_assurance=utilities.session_assurance,
            step_up=utilities.step_up_guard,
            user_view_transformer=transformers.user_view_transformer,
            rate_limit_registry=registries.request_rate_limit_registry,
            product_events=facilitators.product_events,
            platform_admins=registries.platform_admin_registry,
            sign_in_notices=facilitators.sign_in_notice_facilitator,
            storage_scope=utilities.storage_scope,
            app_settings=config.app_settings,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
    )
