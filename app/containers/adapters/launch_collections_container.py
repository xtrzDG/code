from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.billing import OnboardingRequestDocument
from app.schemas.domain.public_slugs import PublicSlugClaimDocument
from app.schemas.domain.setup import (
    ActivationEventDocument,
    AssistantApplyDocument,
    NudgeSentDocument,
    SetupStateDocument,
)
from app.schemas.domain.website_imports import WebsiteImportDocument


class LaunchCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of the guided launch (migration 1044): each
    business's milestones, the setup steps it skipped and its current
    "Apply changes"; of sharing the live assistant (1052): the public chat
    addresses businesses took; and its current knowledge import from its
    website (migration 1054), which the wizard offers too; and of the
    activation follow-up (1080): the nudges sent and the done-for-you setup
    requests. A sibling of
    DocumentCollectionsContainer with the same storage factory (Postgres
    with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    activation_event_collection = document_collection(
        ActivationEventDocument,
        "activation_events",
        config,
        clients,
        utilities,
        time_provider,
    )
    setup_state_collection = document_collection(
        SetupStateDocument, "setup_states", config, clients, utilities, time_provider
    )
    assistant_apply_collection = document_collection(
        AssistantApplyDocument,
        "assistant_applies",
        config,
        clients,
        utilities,
        time_provider,
    )
    public_slug_claim_collection = document_collection(
        PublicSlugClaimDocument,
        "public_slug_claims",
        config,
        clients,
        utilities,
        time_provider,
    )
    website_import_collection = document_collection(
        WebsiteImportDocument,
        "website_imports",
        config,
        clients,
        utilities,
        time_provider,
    )
    nudge_sent_collection = document_collection(
        NudgeSentDocument, "nudges_sent", config, clients, utilities, time_provider
    )
    onboarding_request_collection = document_collection(
        OnboardingRequestDocument,
        "onboarding_requests",
        config,
        clients,
        utilities,
        time_provider,
    )
