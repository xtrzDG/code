"""
The providers of the platform's safety switches and watchers, for the
spend guard's container: the daily budget stop's spend gauge, the global
pause, the platform admin's check and the daily payment reconciliation
with its read-only provider reader (1230).
"""

from dependency_injector.providers import Factory, Singleton

from app.adapters.payments.payment_status_reader_adapter import (
    PaymentStatusReaderAdapter,
)
from app.containers.config import ConfigContainer
from app.containers.factories import build_flitt_client
from app.containers.payment_factories import build_stripe_client
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.platform_safety import PaymentStatusReaderAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.registries.limits.platform_spend_gauge_registry import (
    PlatformSpendGaugeRegistry,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.payment_reconciliation import (
    PaymentReconciliationQuery,
    PaymentReconciliationView,
)
from app.schemas.dto.platform_pause import (
    PlatformPauseCommand,
    PlatformPauseQuery,
    PlatformPauseView,
)
from app.use_cases.admin.authorize_platform_admin_use_case import (
    AuthorizePlatformAdminUseCase,
)
from app.use_cases.billing.reconciliation.get_payment_reconciliation_use_case import (
    GetPaymentReconciliationUseCase,
)
from app.use_cases.billing.reconciliation.reconcile_payments_use_case import (
    ReconcilePaymentsUseCase,
)
from app.use_cases.spend_guard.platform_pause.get_platform_pause_use_case import (
    GetPlatformPauseUseCase,
)
from app.use_cases.spend_guard.platform_pause.set_platform_pause_use_case import (
    SetPlatformPauseUseCase,
)


def platform_spend_gauge(
    repositories: RepositoriesContainer, utilities: UtilitiesContainer
) -> Singleton[PlatformSpendGaugeRegistry]:
    return Singleton(
        PlatformSpendGaugeRegistry,
        usage_spend_repo=repositories.usage_spend_repo,
        storage_scope=utilities.storage_scope,
    )


def platform_admin_check(
    repositories: RepositoriesContainer,
    registries: RegistriesContainer,
    utilities: UtilitiesContainer,
) -> Factory[PlatformAdminCheck]:
    return Factory(
        AuthorizePlatformAdminUseCase,
        user_repo=repositories.user_repo,
        session_assurance=utilities.session_assurance,
        platform_admins=registries.platform_admin_registry,
    )


def build_payment_status_reader(
    settings: AppSettings,
) -> PaymentStatusReaderAdapterContract:
    """Flitt and Stripe read with clients of their own (a daily job's calls)."""

    return PaymentStatusReaderAdapter(
        flitt_client=build_flitt_client(settings),
        stripe_client=build_stripe_client(settings),
    )


def platform_pause_use_cases(
    config: ConfigContainer,
    repositories: RepositoriesContainer,
    utilities: UtilitiesContainer,
    time_provider: TimeProviderContainer,
    admin_check: Factory[PlatformAdminCheck],
    gauge: Singleton[PlatformSpendGaugeRegistry],
) -> tuple[
    Factory[UseCaseContract[PlatformPauseQuery, PlatformPauseView]],
    Factory[UseCaseContract[PlatformPauseCommand, PlatformPauseView]],
]:
    """The admin's look at the brakes, and the SUPER admin's pause."""

    settings = config.app_settings.provided.spend_guard
    return (
        Factory(
            GetPlatformPauseUseCase,
            authorize_platform_admin=admin_check,
            platform_pause_repo=repositories.platform_pause_repo,
            platform_spend_gauge=gauge,
            settings=settings,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
        Factory(
            SetPlatformPauseUseCase,
            authorize_platform_admin=admin_check,
            platform_pause_repo=repositories.platform_pause_repo,
            platform_spend_gauge=gauge,
            audit_log_repo=repositories.audit_log_repo,
            step_up=utilities.step_up_guard,
            settings=settings,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
    )


def payment_reconciliation_use_cases(
    config: ConfigContainer,
    repositories: RepositoriesContainer,
    utilities: UtilitiesContainer,
    time_provider: TimeProviderContainer,
    admin_check: Factory[PlatformAdminCheck],
) -> tuple[
    Factory[UseCaseContract[JobTick, JobReport]],
    Factory[UseCaseContract[PaymentReconciliationQuery, PaymentReconciliationView]],
]:
    """The daily reconciliation job and the admin's view of its result."""

    return (
        Factory(
            ReconcilePaymentsUseCase,
            business_repo=repositories.business_repo,
            payment_order_repo=repositories.payment_order_repo,
            payment_status_reader=Singleton(
                build_payment_status_reader, settings=config.app_settings
            ),
            reconciliation_repo=repositories.payment_reconciliation_repo,
            storage_scope=utilities.storage_scope,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
        Factory(
            GetPaymentReconciliationUseCase,
            authorize_platform_admin=admin_check,
            reconciliation_repo=repositories.payment_reconciliation_repo,
            business_repo=repositories.business_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
    )
