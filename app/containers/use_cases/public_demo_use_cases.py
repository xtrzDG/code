from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.config import ConfigContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.conversations import InboundMessage
from app.schemas.dto.public_demo import (
    PublicDemoBusinessIds,
    PublicDemoCard,
    PublicDemoCardQuery,
    PublicDemoListQuery,
    PublicDemoMessageCommand,
    PublicDemoReply,
    PublicDemoTurnOutcome,
)
from app.use_cases.demo.public.admit_public_demo_message_use_case import (
    AdmitPublicDemoMessageUseCase,
)
from app.use_cases.demo.public.describe_public_demo_use_case import (
    DescribePublicDemoUseCase,
)
from app.use_cases.demo.public.list_public_demo_businesses_use_case import (
    ListPublicDemoBusinessesUseCase,
)
from app.use_cases.demo.public.summarize_public_demo_reply_use_case import (
    SummarizePublicDemoReplyUseCase,
)


class PublicDemoUseCasesContainer(containers.DeclarativeContainer):
    """
    The landing page's sandbox demos (PUBLIC_DEMO_BUSINESS_IDS): which
    businesses, each described for the page, a visitor's message admitted
    within the demo limits, and the sandbox turn told back.
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    list_public_demo_businesses_use_case: Factory[
        UseCaseContract[PublicDemoListQuery, PublicDemoBusinessIds]
    ] = Factory(
        ListPublicDemoBusinessesUseCase,
        public_demo_directory=registries.public_demo_directory,
    )
    describe_public_demo_use_case: Factory[
        UseCaseContract[PublicDemoCardQuery, PublicDemoCard]
    ] = Factory(
        DescribePublicDemoUseCase,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        niche_template_registry=registries.niche_template_registry,
        localized_text_resolver=utilities.localized_text_resolver,
        language_detector=utilities.language_detector,
    )
    admit_public_demo_message_use_case: Factory[
        UseCaseContract[PublicDemoMessageCommand, InboundMessage]
    ] = Factory(
        AdmitPublicDemoMessageUseCase,
        public_demo_directory=registries.public_demo_directory,
        business_repo=repositories.business_repo,
        rate_limit_registry=registries.request_rate_limit_registry,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    summarize_public_demo_reply_use_case: Factory[
        UseCaseContract[PublicDemoTurnOutcome, PublicDemoReply]
    ] = Factory(
        SummarizePublicDemoReplyUseCase,
        message_repo=repositories.message_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
