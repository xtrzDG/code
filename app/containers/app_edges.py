from dependency_injector import containers
from dependency_injector.providers import Container

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.adapters.analytics_collections_container import (
    AnalyticsCollectionsContainer,
)
from app.containers.adapters.feedback_collections_container import (
    FeedbackCollectionsContainer,
)
from app.containers.adapters.inbox_collections_container import (
    InboxCollectionsContainer,
)
from app.containers.adapters.invoicing_collections_container import (
    InvoicingCollectionsContainer,
)
from app.containers.adapters.legal_collections_container import (
    LegalCollectionsContainer,
)
from app.containers.adapters.media_collections_container import (
    MediaCollectionsContainer,
)
from app.containers.adapters.operations_collections_container import (
    OperationsCollectionsContainer,
)
from app.containers.adapters.privacy_collections_container import (
    PrivacyCollectionsContainer,
)
from app.containers.adapters.rate_collections_container import (
    RateCollectionsContainer,
)
from app.containers.adapters.referral_collections_container import (
    ReferralCollectionsContainer,
)
from app.containers.adapters.security_collections_container import (
    SecurityCollectionsContainer,
)
from app.containers.adapters.spend_guard_collections_container import (
    SpendGuardCollectionsContainer,
)
from app.containers.adapters.value_collections_container import (
    ValueCollectionsContainer,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer


class AppEdgesContainer(containers.DeclarativeContainer):
    """
    The edges of the composition root: settings, time, utilities, external
    clients, the adapters and the collection containers that are siblings
    of the adapters' own (one per bounded context that added collections).
    `AppContainer` builds the roles on top of them; tests override these.
    """

    config: ConfigContainer = Container(ConfigContainer)  # type: ignore[assignment]
    time_provider: TimeProviderContainer = Container(  # type: ignore[assignment]
        TimeProviderContainer
    )
    utilities: UtilitiesContainer = Container(  # type: ignore[assignment]
        UtilitiesContainer,
        config=config,
        time_provider=time_provider,
    )
    clients: ClientsContainer = Container(  # type: ignore[assignment]
        ClientsContainer,
        config=config,
    )
    adapters: AdaptersContainer = Container(  # type: ignore[assignment]
        AdaptersContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The team inbox's collections (1053), a sibling of the adapters' own.
    inbox_collections: InboxCollectionsContainer = Container(  # type: ignore[assignment]
        InboxCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # Key management's collection (1063), a sibling as well.
    security_collections: SecurityCollectionsContainer = Container(  # type: ignore[assignment]
        SecurityCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # What the assistant is worth: average check, digests, reports (1061).
    value_collections: ValueCollectionsContainer = Container(  # type: ignore[assignment]
        ValueCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The feedback after visits' collections (1062), another sibling.
    feedback_collections: FeedbackCollectionsContainer = Container(  # type: ignore[assignment]
        FeedbackCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The dated exchange rates' collection (1071), a sibling as well.
    rate_collections: RateCollectionsContainer = Container(  # type: ignore[assignment]
        RateCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The growth analytics' collections (1074), one more sibling.
    analytics_collections: AnalyticsCollectionsContainer = Container(  # type: ignore[assignment]
        AnalyticsCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The collection of files customers send (1081), one more sibling.
    media_collections: MediaCollectionsContainer = Container(  # type: ignore[assignment]
        MediaCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The platform's alerts, backups and incidents (1093), one more sibling.
    operations_collections: OperationsCollectionsContainer = Container(  # type: ignore[assignment]
        OperationsCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The suppression list and the full business exports (1113), one more.
    privacy_collections: PrivacyCollectionsContainer = Container(  # type: ignore[assignment]
        PrivacyCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # Billing details and invoice numbers (1114), one more sibling.
    invoicing_collections: InvoicingCollectionsContainer = Container(  # type: ignore[assignment]
        InvoicingCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The sub-processor change notices (1124), one more sibling.
    legal_collections: LegalCollectionsContainer = Container(  # type: ignore[assignment]
        LegalCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # Spend limits and the websites allowed to show a chat (1142).
    spend_guard_collections: SpendGuardCollectionsContainer = Container(  # type: ignore[assignment]
        SpendGuardCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The credit ledger, notes, health changes, digests (1143), referrals (1150).
    client_care_collections: ReferralCollectionsContainer = Container(  # type: ignore[assignment]
        ReferralCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
