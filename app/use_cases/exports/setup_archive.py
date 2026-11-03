"""
The rest of the business's setup in a full export (Data Act art. 26:
switching takes the whole configuration along), beside
`configuration_archive`: the opening hours' exceptions (closed days and
special hours), the settings of deposits, the waitlist, the return-visit
campaign, visit feedback, the inbox, the assistant and the customers (the
business's own tags), the customer segments, the quick replies and the
team's notes on conversations, each a JSON array like every collection of
the archive. None of them holds a credential: a deposit's payment links
are the pages customers are sent anyway.
"""

from dataclasses import dataclass

from app.contracts.repositories.business_document_pages import (
    BusinessDocumentPagesContract,
)
from app.schemas.domain.assistant_settings import AssistantSettingsDocument
from app.schemas.domain.campaigns import CampaignSettingsDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.customer_segments import CustomerSegmentDocument
from app.schemas.domain.customer_settings import CustomerSettingsDocument
from app.schemas.domain.deposits import DepositSettingsDocument
from app.schemas.domain.feedback import ReviewSettingsDocument
from app.schemas.domain.inbox_settings import InboxSettingsDocument
from app.schemas.domain.quick_replies import QuickReplyLibraryDocument
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.domain.waitlist import WaitlistSettingsDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.exports.archive_pages import DocumentPages
from app.use_cases.shared.document_pages import pages_in_write_order


@dataclass(frozen=True)
class SetupArchive:
    schedule_exception_repo: BusinessDocumentPagesContract[ScheduleExceptionDocument]
    deposit_settings_repo: BusinessDocumentPagesContract[DepositSettingsDocument]
    waitlist_settings_repo: BusinessDocumentPagesContract[WaitlistSettingsDocument]
    campaign_settings_repo: BusinessDocumentPagesContract[CampaignSettingsDocument]
    review_settings_repo: BusinessDocumentPagesContract[ReviewSettingsDocument]
    inbox_settings_repo: BusinessDocumentPagesContract[InboxSettingsDocument]
    assistant_settings_repo: BusinessDocumentPagesContract[AssistantSettingsDocument]
    customer_settings_repo: BusinessDocumentPagesContract[CustomerSettingsDocument]
    customer_segment_repo: BusinessDocumentPagesContract[CustomerSegmentDocument]
    quick_reply_library_repo: BusinessDocumentPagesContract[QuickReplyLibraryDocument]
    conversation_note_repo: BusinessDocumentPagesContract[ConversationNoteDocument]

    def pages(self, business_id: BusinessId) -> dict[str, DocumentPages]:
        """Each file's documents, read a keyset page at a time (none: [])."""

        # Each read alone, so its document type (and its id) is its own.
        exceptions = pages_in_write_order(
            self.schedule_exception_repo, business_id, lambda item: str(item.id)
        )
        deposits = pages_in_write_order(
            self.deposit_settings_repo, business_id, lambda item: str(item.id)
        )
        waitlist = pages_in_write_order(
            self.waitlist_settings_repo, business_id, lambda item: str(item.id)
        )
        campaign = pages_in_write_order(
            self.campaign_settings_repo, business_id, lambda item: str(item.id)
        )
        reviews = pages_in_write_order(
            self.review_settings_repo, business_id, lambda item: str(item.id)
        )
        inbox = pages_in_write_order(
            self.inbox_settings_repo, business_id, lambda item: str(item.id)
        )
        assistant = pages_in_write_order(
            self.assistant_settings_repo, business_id, lambda item: str(item.id)
        )
        customers = pages_in_write_order(
            self.customer_settings_repo, business_id, lambda item: str(item.id)
        )
        segments = pages_in_write_order(
            self.customer_segment_repo, business_id, lambda item: str(item.id)
        )
        replies = pages_in_write_order(
            self.quick_reply_library_repo, business_id, lambda item: str(item.id)
        )
        notes = pages_in_write_order(
            self.conversation_note_repo, business_id, lambda item: str(item.id)
        )
        return {
            "schedule_exceptions": exceptions,
            "deposit_settings": deposits,
            "waitlist_settings": waitlist,
            "campaign_settings": campaign,
            "review_settings": reviews,
            "inbox_settings": inbox,
            "assistant_settings": assistant,
            "customer_settings": customers,
            "customer_segments": segments,
            "quick_reply_libraries": replies,
            "conversation_notes": notes,
        }
