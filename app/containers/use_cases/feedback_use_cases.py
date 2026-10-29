from dependency_injector import containers
from dependency_injector.providers import Dependency, Factory, Singleton

from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.feedback.feedback_dependencies import FeedbackDependencies
from app.containers.feedback.feedback_root import FeedbackRoot
from app.containers.feedback.feedback_use_case_factories import (
    FeedbackUseCaseFactories,
)
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.feedback.customer_signals import CustomerSignalReply


class FeedbackUseCasesContainer(containers.DeclarativeContainer):
    """
    Feedback after visits in the dependency graph: the periodic job that
    asks customers how their visit went, the platform's answers to STOP,
    START and a rating, the review link a customer opens, and Settings →
    Reviews. The context is wired in plain typed Python
    (app/containers/feedback/, ADR 0010); this container holds its one
    root and exposes the use case the conversation turn calls.
    """

    root: Dependency[FeedbackRoot] = Dependency(instance_of=FeedbackRoot)

    answer_customer_signal_use_case: Factory[
        UseCaseContract[PreparedTurn, CustomerSignalReply | None]
    ] = Factory(
        FeedbackUseCaseFactories.answer_customer_signal, root.provided.use_cases
    )


def feedback_root(
    *,
    account_use_cases: AccountUseCasesContainer,
    config: ConfigContainer,
    facilitators: FacilitatorsContainer,
    registries: RegistriesContainer,
    repositories: RepositoriesContainer,
    time_provider: TimeProviderContainer,
    utilities: UtilitiesContainer,
) -> Singleton[FeedbackRoot]:
    """
    The feedback context's one root, its dependencies taken from the graph:
    the single seam between the providers and the typed root (a missing or
    misspelt field fails test_every_provider_of_the_container_resolves).
    """

    return Singleton(
        FeedbackRoot,
        dependencies=Factory(
            FeedbackDependencies,
            authorize_business_access=account_use_cases.authorize_business_access_use_case,
            review_settings_repo=repositories.review_settings_repo,
            feedback_request_repo=repositories.feedback_request_repo,
            business_repo=repositories.business_repo,
            business_profile_repo=repositories.business_profile_repo,
            booking_repo=repositories.booking_repo,
            contact_repo=repositories.contact_repo,
            channel_repo=repositories.channel_repo,
            conversation_repo=repositories.conversation_repo,
            message_repo=repositories.message_repo,
            outbound_message_repo=repositories.outbound_message_repo,
            audit_log_repo=repositories.audit_log_repo,
            job_queue=facilitators.job_queue_facilitator,
            rate_limits=registries.request_rate_limit_registry,
            text_resolver=utilities.localized_text_resolver,
            live_events=facilitators.event_publisher,
            suppression_list=facilitators.suppression_list,
            storage_scope=utilities.storage_scope,
            wall_clock=time_provider.microsecond_wall_clock,
            app_base_url=config.app_settings.provided.app_base_url,
        ),
    )
