from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.channel_clients import MetaGraphApiClientContract
from app.contracts.channels import ChannelAdapterContract
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.meta_connection import (
    MetaConnectionStateRepoContract,
    MetaOAuthClientContract,
    MetaPagesClientContract,
    WhatsAppOnboardingClientContract,
)
from app.contracts.privacy import SuppressionListContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.delivery_repositories import (
    InboundEventRepoContract,
    OutboundMessageRepoContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.storage import StorageScopeContract, StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.deliveries import InboundAnswer, InboundEventClaim, InboundFailure
from app.schemas.dto.jobs import QueuedJobInput


@dataclass(frozen=True, slots=True, kw_only=True)
class MetaConnectionDependencies:
    """
    Everything Meta's self-serve connection (R15, migration 1212) takes from
    the rest of the application, as contracts: the owner's access and the
    step-up, the Facebook sign-ins' repository, Meta's clients, the channel
    it connects and its sealed tokens, the business's closure (a closing
    business connects nothing), the inbox and outbox the comment
    replies go through, and the inbox's claim, finish and release of the
    worker's job. The only place the dependency graph meets the typed root
    (the provider in app/containers/use_cases/meta_connection_root_provider.py
    fills it).
    """

    authorize_business_access: UseCaseContract[BusinessAccessRequest, BusinessDocument]
    step_up: StepUpGuardContract
    state_repo: MetaConnectionStateRepoContract
    oauth_client: MetaOAuthClientContract
    pages_client: MetaPagesClientContract
    onboarding_client: WhatsAppOnboardingClientContract
    meta_client: MetaGraphApiClientContract
    instagram_adapter: ChannelAdapterContract
    channel_repo: ChannelRepoContract
    closure_repo: BusinessClosureRepoContract
    contact_repo: ContactRepoContract
    inbound_event_repo: InboundEventRepoContract
    outbound_message_repo: OutboundMessageRepoContract
    audit_log_repo: AuditLogRepoContract
    secret_cipher: SecretCipherAdapterContract
    suppression_list: SuppressionListContract
    job_queue: JobQueueFacilitatorContract
    rate_limit_registry: RequestRateLimitRegistryContract
    product_events: RecordProductEventFacilitatorContract
    claim_inbound_event: UseCaseContract[QueuedJobInput, InboundEventClaim | None]
    finish_inbound_event: UseCaseContract[InboundAnswer, InboundEventDocument | None]
    release_inbound_event: UseCaseContract[InboundFailure, InboundEventDocument | None]
    storage_scope: StorageScopeContract
    unit_of_work: StorageUnitOfWorkContract
    app_settings: AppSettings
    wall_clock: WallClock[Microseconds]
