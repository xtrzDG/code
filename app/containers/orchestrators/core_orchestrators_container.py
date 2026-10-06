from dependency_injector import containers
from dependency_injector.providers import Container, DependenciesContainer

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.orchestrators.account_orchestrators import (
    AccountOrchestratorsContainer,
)
from app.containers.orchestrators.admin_action_orchestrators import (
    AdminActionOrchestratorsContainer,
)
from app.containers.orchestrators.analytics_orchestrators import (
    AnalyticsOrchestratorsContainer,
)
from app.containers.orchestrators.compliance_orchestrators import (
    ComplianceOrchestratorsContainer,
)
from app.containers.orchestrators.data_task_orchestrators import (
    DataTaskOrchestratorsContainer,
)
from app.containers.orchestrators.demo_orchestrators import DemoOrchestratorsContainer
from app.containers.orchestrators.legal_orchestrators import (
    LegalOrchestratorsContainer,
)
from app.containers.orchestrators.platform_ops_orchestrators import (
    PlatformOpsOrchestratorsContainer,
)
from app.containers.orchestrators.platform_orchestrators import (
    PlatformOrchestratorsContainer,
)
from app.containers.orchestrators.privacy_orchestrators import (
    PrivacyOrchestratorsContainer,
)
from app.containers.orchestrators.public_demo_orchestrators import (
    PublicDemoOrchestratorsContainer,
)
from app.containers.orchestrators.referral_orchestrators import (
    ReferralOrchestratorsContainer,
)
from app.containers.orchestrators.reliability_orchestrators import (
    ReliabilityOrchestratorsContainer,
)
from app.containers.orchestrators.security_orchestrators import (
    SecurityOrchestratorsContainer,
)
from app.containers.orchestrators.spend_guard_orchestrators import (
    SpendGuardOrchestratorsContainer,
)
from app.containers.orchestrators.telemetry_orchestrators import (
    TelemetryOrchestratorsContainer,
)
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.use_cases_container import UseCasesContainer
from app.containers.utilities import UtilitiesContainer


class CoreOrchestratorsContainer(containers.DeclarativeContainer):
    """
    The edges of the orchestrators and the contexts of the platform itself:
    accounts, compliance, privacy and legal, the public demos, platform
    administration and operations (alerts, telemetry, data tasks, spend,
    admin actions, security), analytics, the demo data and referrals.
    `OrchestratorsContainer` adds a business's own work on top.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    use_cases: UseCasesContainer = composed_container_edge(UseCasesContainer)  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    accounts: AccountOrchestratorsContainer = Container(  # type: ignore[assignment]
        AccountOrchestratorsContainer,
        account_use_cases=use_cases.accounts,
        catalog_use_cases=use_cases.catalog,
        assistant_use_cases=use_cases.assistants,
    )
    compliance: ComplianceOrchestratorsContainer = Container(  # type: ignore[assignment]
        ComplianceOrchestratorsContainer,
        compliance_use_cases=use_cases.compliance,
    )
    privacy: PrivacyOrchestratorsContainer = Container(  # type: ignore[assignment]
        PrivacyOrchestratorsContainer,
        privacy_use_cases=use_cases.privacy,
    )
    legal: LegalOrchestratorsContainer = Container(  # type: ignore[assignment]
        LegalOrchestratorsContainer,
        legal_use_cases=use_cases.legal,
    )
    public_demos: PublicDemoOrchestratorsContainer = Container(  # type: ignore[assignment]
        PublicDemoOrchestratorsContainer,
        public_demo_use_cases=use_cases.public_demos,
        utilities=utilities,
    )
    platform: PlatformOrchestratorsContainer = Container(  # type: ignore[assignment]
        PlatformOrchestratorsContainer,
        platform_use_cases=use_cases.platform,
    )
    telemetry: TelemetryOrchestratorsContainer = Container(  # type: ignore[assignment]
        TelemetryOrchestratorsContainer, telemetry_use_cases=use_cases.telemetry
    )
    reliability: ReliabilityOrchestratorsContainer = Container(  # type: ignore[assignment]
        ReliabilityOrchestratorsContainer,
        reliability_use_cases=use_cases.reliability,
        platform_ops_use_cases=use_cases.platform_ops,
    )
    platform_ops: PlatformOpsOrchestratorsContainer = Container(  # type: ignore[assignment]
        PlatformOpsOrchestratorsContainer,
        platform_ops_use_cases=use_cases.platform_ops,
        help_use_cases=use_cases.help,
    )
    data_tasks: DataTaskOrchestratorsContainer = Container(  # type: ignore[assignment]
        DataTaskOrchestratorsContainer, data_task_use_cases=use_cases.data_tasks
    )
    spend_guard: SpendGuardOrchestratorsContainer = Container(  # type: ignore[assignment]
        SpendGuardOrchestratorsContainer,
        spend_guard_use_cases=use_cases.spend_guard,
        platform_ops_use_cases=use_cases.platform_ops,
    )
    admin_actions: AdminActionOrchestratorsContainer = Container(  # type: ignore[assignment]
        AdminActionOrchestratorsContainer,
        admin_action_use_cases=use_cases.admin_actions,
    )
    security: SecurityOrchestratorsContainer = Container(  # type: ignore[assignment]
        SecurityOrchestratorsContainer,
        security_use_cases=use_cases.security,
        mfa_use_cases=use_cases.mfa,
    )
    analytics: AnalyticsOrchestratorsContainer = Container(  # type: ignore[assignment]
        AnalyticsOrchestratorsContainer,
        analytics_use_cases=use_cases.analytics,
    )
    demo: DemoOrchestratorsContainer = Container(  # type: ignore[assignment]
        DemoOrchestratorsContainer,
        demo_use_cases=use_cases.demo,
        assistant_use_cases=use_cases.assistants,
    )
    referrals: ReferralOrchestratorsContainer = Container(  # type: ignore[assignment]
        ReferralOrchestratorsContainer,
        referral_use_cases=use_cases.referrals,
    )
