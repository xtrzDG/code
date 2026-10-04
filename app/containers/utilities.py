from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.contracts.health import ReadinessMemoryContract
from app.contracts.session_assurance import (
    SessionAssuranceContract,
    StepUpGuardContract,
)
from app.contracts.storage import StorageScopeContract
from app.utilities.conversations.language_detector import LanguageDetector
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from app.utilities.observability.readiness_memory import ReadinessMemory
from app.utilities.security.require_recent_authentication import (
    RequireRecentAuthentication,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from app.utilities.storage.storage_scope_context import StorageScopeContext


class UtilitiesContainer(containers.DeclarativeContainer):
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    phone_number_parser: Singleton[PhoneNumberParser] = Singleton(PhoneNumberParser)
    localized_text_resolver: Singleton[LocalizedTextResolver] = Singleton(
        LocalizedTextResolver
    )
    language_detector: Singleton[LanguageDetector] = Singleton(LanguageDetector)
    # One scope shared by every Postgres collection of the process, and by
    # the operators, orchestrators and the worker that enter it.
    storage_scope: Singleton[StorageScopeContract] = Singleton(StorageScopeContext)
    # What GET /readyz remembers between probes of this process.
    readiness_memory: Singleton[ReadinessMemoryContract] = Singleton(ReadinessMemory)
    # The signed-in session of the request being served (bound by the HTTP
    # gateway), and the step-up check of every sensitive action.
    session_assurance: Singleton[SessionAssuranceContract] = Singleton(
        SessionAssuranceContext
    )
    step_up_guard: Singleton[StepUpGuardContract] = Singleton(
        RequireRecentAuthentication,
        session_assurance=session_assurance,
        wall_clock=time_provider.microsecond_wall_clock,
        max_age=config.app_settings.provided.step_up_max_age_seconds,
    )
