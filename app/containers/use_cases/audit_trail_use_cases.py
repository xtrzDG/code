from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.audit_chain_views import (
    AdminAuditChainsQuery,
    AuditChainOverview,
    AuditChainStatusQuery,
    AuditChainStatusView,
    PlatformAuditLogPage,
    PlatformAuditLogQuery,
)
from app.schemas.dto.audit_trail import AuditLogPurgeCommand, AuditLogPurgeReport
from app.schemas.dto.jobs import JobReport, JobTick
from app.use_cases.admin.audit.get_audit_chain_overview_use_case import (
    GetAuditChainOverviewUseCase,
)
from app.use_cases.admin.audit.list_platform_audit_log_use_case import (
    ListPlatformAuditLogUseCase,
)
from app.use_cases.compliance.audit_chain.get_audit_chain_status_use_case import (
    GetAuditChainStatusUseCase,
)
from app.use_cases.compliance.audit_chain.verify_audit_chains_use_case import (
    VerifyAuditChainsUseCase,
)
from app.use_cases.maintenance.purge_audit_log_use_case import PurgeAuditLogUseCase


class AuditTrailUseCasesContainer(containers.DeclarativeContainer):
    """
    The audit log's hash chains (R13-AUDIT-TRAIL, migration 1193): the
    owner's view of the business's chain, the platform admin's audit view
    and chain overview, and the daily `verify_audit_chain` job.
    """

    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    platform_use_cases: PlatformUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_audit_chain_status_use_case: Factory[
        UseCaseContract[AuditChainStatusQuery, AuditChainStatusView]
    ] = Factory(
        GetAuditChainStatusUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        audit_chain_repo=repositories.audit_chain_repo,
    )
    get_audit_chain_overview_use_case: Factory[
        UseCaseContract[AdminAuditChainsQuery, AuditChainOverview]
    ] = Factory(
        GetAuditChainOverviewUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        audit_chain_repo=repositories.audit_chain_repo,
    )
    list_platform_audit_log_use_case: Factory[
        UseCaseContract[PlatformAuditLogQuery, PlatformAuditLogPage]
    ] = Factory(
        ListPlatformAuditLogUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        audit_activity_repo=repositories.audit_activity_repo,
    )
    # The daily `verify_audit_chain` job.
    verify_audit_chains_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            VerifyAuditChainsUseCase,
            business_repo=repositories.business_repo,
            chain_repo=repositories.audit_chain_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    # `workshop purge-audit-log`, an operator's command.
    purge_audit_log_use_case: Factory[
        UseCaseContract[AuditLogPurgeCommand, AuditLogPurgeReport]
    ] = Factory(
        PurgeAuditLogUseCase,
        purges=repositories.audit_chain_purges,
        business_repo=repositories.business_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
