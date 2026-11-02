"""The rebooking campaign's job over the growth world, and its visits."""

from datetime import datetime

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.gateways.worker.periodic.growth_jobs import RUN_REBOOKING_CAMPAIGNS_JOB
from app.repositories.campaign_repositories import CampaignSettingsRepository
from app.repositories.contact_activity_repository import ContactActivityRepository
from app.repositories.customer_history_repository import CustomerHistoryRepository
from app.repositories.customer_repositories import CustomerSegmentRepository
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.campaigns import CampaignAudience, RebookingRuleKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.marketing_consent import (
    CURRENT_MARKETING_CONSENT_TEXT,
    MarketingConsentSource,
)
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.campaigns import (
    CampaignMessageDocument,
    CampaignSettingsDocument,
)
from app.schemas.domain.contacts import ContactDocument, MarketingConsent
from app.schemas.domain.conversations import CallDocument
from app.schemas.domain.customer_segments import (
    CustomerSegmentDocument,
    SegmentRules,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.campaigns.constrained_integers import (
    CampaignMonthlyCap,
    RebookingDelayDays,
)
from app.schemas.typings.contacts.constrained_strings import SegmentName
from app.schemas.typings.contacts.prefixed_id import CustomerSegmentId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.campaigns.campaign_writer import CampaignWriter
from app.use_cases.campaigns.run_rebooking_campaigns_use_case import (
    RunRebookingCampaignsUseCase,
)
from app.use_cases.shared.customer_segment_members import SegmentReaders
from app.utilities.campaigns.campaign_keys import campaign_settings_id_of
from tests.operations.builders import DEFAULT_NOW
from tests.waitlist.growth_world import GrowthWorld


class CampaignWorld(GrowthWorld):
    """The restaurant with its campaign settings, segments and the hourly job."""

    def __init__(self, now: datetime = DEFAULT_NOW) -> None:
        super().__init__(now)
        self.campaign_settings_repo = CampaignSettingsRepository(
            InMemoryDocumentCollectionAdapter(CampaignSettingsDocument)
        )
        self.segment_repo = CustomerSegmentRepository(
            InMemoryDocumentCollectionAdapter(CustomerSegmentDocument)
        )
        self.readers = SegmentReaders(
            card_repo=self.contact_repo,
            activity_repo=ContactActivityRepository(
                self.conversation_collection,
                self.booking_collection,
                self.lead_collection,
            ),
            history_repo=CustomerHistoryRepository(
                self.conversation_collection,
                self.booking_collection,
                InMemoryDocumentCollectionAdapter(CallDocument),
            ),
        )

    def enable(
        self,
        rule_kind: RebookingRuleKind = RebookingRuleKind.REBOOK,
        delay_days: int = 30,
        monthly_cap: int = 100,
        segment: CustomerSegmentDocument | None = None,
        is_enabled: bool = True,
    ) -> None:
        now = self.clock.now_microseconds()
        self.campaign_settings_repo.save(
            CampaignSettingsDocument(
                id=campaign_settings_id_of(self.business.id),
                business_id=self.business.id,
                is_enabled=is_enabled,
                rule_kind=rule_kind,
                delay_days=RebookingDelayDays(delay_days),
                audience=(
                    CampaignAudience.ALL_CUSTOMERS
                    if segment is None
                    else CampaignAudience.SEGMENT
                ),
                segment_id=None if segment is None else segment.id,
                monthly_cap=CampaignMonthlyCap(monthly_cap),
                created_at=now,
                updated_at=now,
            )
        )

    def vip_segment(self) -> CustomerSegmentDocument:
        now = self.clock.now_microseconds()
        segment = CustomerSegmentDocument(
            id=CustomerSegmentId(),
            business_id=self.business.id,
            name=SegmentName("VIP guests"),
            rules=SegmentRules(vip_only=True),
            created_by=UserId(),
            created_at=now,
            updated_at=now,
        )
        self.segment_repo.save(segment)
        return segment

    def guest(
        self,
        name: str,
        language: str = "ru",
        phone: str | None = None,
        has_consent: bool = True,
    ) -> ContactDocument:
        """A guest in Telegram; one who agreed to marketing unless told."""

        guest = super().guest(name, language, phone)
        if has_consent:
            self.agree(guest)
        return guest

    def agree(self, guest: ContactDocument) -> None:
        """The guest ticked the marketing box on their booking page."""

        def record(stored: ContactDocument) -> None:
            stored.marketing_consent = MarketingConsent(
                given_at=self.clock.now_microseconds(),
                source=MarketingConsentSource.BOOKING_PAGE,
                text_version=CURRENT_MARKETING_CONSENT_TEXT,
            )

        self.contact_repo.change_card(self.business.id, guest.id, record)

    def make_vip(self, guest: ContactDocument) -> None:
        def mark(stored: ContactDocument) -> None:
            stored.is_vip = True

        self.contact_repo.change_card(self.business.id, guest.id, mark)

    def visit(
        self,
        guest: ContactDocument,
        starts: str,
        ends: str,
        status: BookingStatus = BookingStatus.COMPLETED,
        source_channel: ChannelKind = ChannelKind.TELEGRAM,
    ) -> BookingDocument:
        """A booking the guest made in `source_channel` (their Telegram chat)."""

        booking = self.add_booking(
            self.business, self.table_for_four, guest, starts, ends, status=status
        )
        booking.language = guest.language
        booking.source_channel = source_channel
        self.booking_repo.save(booking)
        return booking

    def run_campaigns(self) -> JobReport:
        return RunRebookingCampaignsUseCase(
            campaign_settings_repo=self.campaign_settings_repo,
            campaign_message_repo=self.campaign_message_repo,
            business_repo=self.business_repo,
            booking_repo=self.booking_repo,
            contact_repo=self.contact_repo,
            customer_segment_repo=self.segment_repo,
            segment_readers=self.readers,
            writer=CampaignWriter(
                message_repo=self.campaign_message_repo,
                routing=self.routing,
                sender=self.sender,
                text_resolver=self.resolver,
                live_events=self.live_events,
                suppression_list=self.suppression_list,
                whatsapp_template=None,
            ),
            wall_clock=self.clock.wall_clock,
        ).run(
            JobTick(
                job_name=RUN_REBOOKING_CAMPAIGNS_JOB,
                scheduled_at=self.clock.now_microseconds(),
            )
        )

    def messages_of(self, guest: ContactDocument) -> list[CampaignMessageDocument]:
        return self.campaign_message_repo.list_of_contact(self.business.id, guest.id)
