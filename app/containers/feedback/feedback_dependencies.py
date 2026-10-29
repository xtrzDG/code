from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.privacy import SuppressionListContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
    ReviewSettingsRepoContract,
)
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl


@dataclass(frozen=True, slots=True, kw_only=True)
class FeedbackDependencies:
    """
    Everything the feedback context takes from the rest of the application,
    as contracts: repositories, the platform's facilitators and utilities,
    the access check of the cabinet and the settings it reads. The only
    place the dependency graph meets the typed root (the provider in
    app/containers/use_cases/feedback_use_cases.py fills it).
    """

    authorize_business_access: UseCaseContract[BusinessAccessRequest, BusinessDocument]
    review_settings_repo: ReviewSettingsRepoContract
    feedback_request_repo: FeedbackRequestRepoContract
    business_repo: BusinessRepoContract
    business_profile_repo: BusinessProfileRepoContract
    booking_repo: BookingRepoContract
    contact_repo: ContactRepoContract
    channel_repo: ChannelRepoContract
    conversation_repo: ConversationRepoContract
    message_repo: MessageRepoContract
    outbound_message_repo: OutboundMessageRepoContract
    audit_log_repo: AuditLogRepoContract
    job_queue: JobQueueFacilitatorContract
    rate_limits: RequestRateLimitRegistryContract
    text_resolver: LocalizedTextResolverContract
    live_events: EventPublisherFacilitatorContract
    suppression_list: SuppressionListContract
    storage_scope: StorageScopeContract
    wall_clock: WallClock[Microseconds]
    app_base_url: PublicBaseUrl | None
