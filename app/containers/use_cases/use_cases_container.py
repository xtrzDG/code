from dependency_injector.providers import Container, Factory

from app.containers.use_cases.admin_action_use_cases import AdminActionUseCasesContainer
from app.containers.use_cases.analytics_use_cases import AnalyticsUseCasesContainer
from app.containers.use_cases.business_use_cases_container import (
    BusinessUseCasesContainer,
)
from app.containers.use_cases.core_use_cases_container import CoreUseCasesContainer
from app.containers.use_cases.data_task_use_cases import DataTaskUseCasesContainer
from app.containers.use_cases.demo_use_cases import DemoUseCasesContainer
from app.containers.use_cases.feedback_use_cases import FeedbackUseCasesContainer
from app.containers.use_cases.platform_ops_use_cases import (
    PlatformOpsUseCasesContainer,
)
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.containers.use_cases.referral_use_cases import ReferralUseCasesContainer
from app.containers.use_cases.security_use_cases import SecurityUseCasesContainer
from app.containers.use_cases.sharing_use_cases import SharingUseCasesContainer
from app.containers.use_cases.subscription_lifecycle_use_cases import (
    SubscriptionLifecycleUseCasesContainer,
)
from app.containers.use_cases.telemetry_use_cases import TelemetryUseCasesContainer
from app.containers.use_cases.value_use_cases import ValueUseCasesContainer
from app.use_cases.example_use_case import ExampleUseCase


class UseCasesContainer(BusinessUseCasesContainer):
    """
    Every use case, one child container per bounded context, typed by its
    contract, so the orchestrator, pipeline and operator chains built on them
    are checked; the edges and the contexts the others build on come from
    `CoreUseCasesContainer`, a business's own work from
    `BusinessUseCasesContainer`. Use cases are stateless Factories, except
    ones holding a cache; a context running another's use cases gets that
    (earlier) child container as edge.
    """

    platform: PlatformUseCasesContainer = Container(  # type: ignore[assignment]
        PlatformUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
        billing_use_cases=BusinessUseCasesContainer.billing,
    )
    security: SecurityUseCasesContainer = Container(  # type: ignore[assignment]
        SecurityUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        clients=CoreUseCasesContainer.clients,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
        platform_use_cases=platform,
        account_use_cases=CoreUseCasesContainer.accounts,
    )
    # Post-deploy data tasks: the batch worker's runs, the admin card.
    data_tasks: DataTaskUseCasesContainer = Container(  # type: ignore[assignment]
        DataTaskUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        config=CoreUseCasesContainer.config,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        platform_use_cases=platform,
    )
    platform_ops: PlatformOpsUseCasesContainer = Container(  # type: ignore[assignment]
        PlatformOpsUseCasesContainer,
        data_task_use_cases=data_tasks,
        adapters=CoreUseCasesContainer.adapters,
        clients=CoreUseCasesContainer.clients,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
        platform_use_cases=platform,
    )
    sharing: SharingUseCasesContainer = Container(  # type: ignore[assignment]
        SharingUseCasesContainer,
        time_provider=CoreUseCasesContainer.time_provider,
        account_use_cases=CoreUseCasesContainer.accounts,
        facilitators=CoreUseCasesContainer.facilitators,
        repositories=CoreUseCasesContainer.repositories,
        registries=CoreUseCasesContainer.registries,
        utilities=CoreUseCasesContainer.utilities,
        config=CoreUseCasesContainer.config,
    )
    value: ValueUseCasesContainer = Container(  # type: ignore[assignment]
        ValueUseCasesContainer,
        time_provider=CoreUseCasesContainer.time_provider,
        account_use_cases=CoreUseCasesContainer.accounts,
        facilitators=CoreUseCasesContainer.facilitators,
        repositories=CoreUseCasesContainer.repositories,
        registries=CoreUseCasesContainer.registries,
        adapters=CoreUseCasesContainer.adapters,
        config=CoreUseCasesContainer.config,
    )
    feedback: FeedbackUseCasesContainer = Container(  # type: ignore[assignment]
        FeedbackUseCasesContainer,
        time_provider=CoreUseCasesContainer.time_provider,
        account_use_cases=CoreUseCasesContainer.accounts,
        facilitators=CoreUseCasesContainer.facilitators,
        repositories=CoreUseCasesContainer.repositories,
        registries=CoreUseCasesContainer.registries,
        utilities=CoreUseCasesContainer.utilities,
        config=CoreUseCasesContainer.config,
    )
    analytics: AnalyticsUseCasesContainer = Container(  # type: ignore[assignment]
        AnalyticsUseCasesContainer,
        time_provider=CoreUseCasesContainer.time_provider,
        facilitators=CoreUseCasesContainer.facilitators,
        platform_use_cases=platform,
        repositories=CoreUseCasesContainer.repositories,
        billing_use_cases=BusinessUseCasesContainer.billing,
        registries=CoreUseCasesContainer.registries,
    )
    demo: DemoUseCasesContainer = Container(  # type: ignore[assignment]
        DemoUseCasesContainer,
        time_provider=CoreUseCasesContainer.time_provider,
        facilitators=CoreUseCasesContainer.facilitators,
        repositories=CoreUseCasesContainer.repositories,
        registries=CoreUseCasesContainer.registries,
        adapters=CoreUseCasesContainer.adapters,
        config=CoreUseCasesContainer.config,
    )
    admin_actions: AdminActionUseCasesContainer = Container(  # type: ignore[assignment]
        AdminActionUseCasesContainer,
        platform_use_cases=platform,
        adapters=CoreUseCasesContainer.adapters,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        voice_use_cases=BusinessUseCasesContainer.voice,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
    )
    referrals: ReferralUseCasesContainer = Container(  # type: ignore[assignment]
        ReferralUseCasesContainer,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        platform_use_cases=platform,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
        account_use_cases=CoreUseCasesContainer.accounts,
    )
    subscription_lifecycle: SubscriptionLifecycleUseCasesContainer = Container(  # type: ignore[assignment]
        SubscriptionLifecycleUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        transformers=CoreUseCasesContainer.transformers,
        utilities=CoreUseCasesContainer.utilities,
        account_use_cases=CoreUseCasesContainer.accounts,
        billing_use_cases=BusinessUseCasesContainer.billing,
    )
    telemetry: TelemetryUseCasesContainer = Container(  # type: ignore[assignment]
        TelemetryUseCasesContainer,
        platform_use_cases=platform,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
    )

    # --- Template example (keeps its concrete type).
    example_use_case: Factory[ExampleUseCase] = Factory(ExampleUseCase)
