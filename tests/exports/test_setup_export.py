"""
A full export takes the rest of the business's setup along (Data Act art.
26, GOV-07): the opening hours' exceptions, the settings of deposits, the
waitlist, the campaign, visit feedback, the inbox, the assistant and the
customers, the customer segments, the quick replies and the team's notes,
each file the business's own documents only, read a page at a time; a
payment page's sealed (key-bearing) address never leaves.
"""

from dataclasses import replace

from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.assistant_settings_repository import (
    AssistantSettingsRepository,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.campaign_repositories import CampaignSettingsRepository
from app.repositories.customer_repositories import (
    CustomerSegmentRepository,
    CustomerSettingsRepository,
)
from app.repositories.deposit_repositories import DepositSettingsRepository
from app.repositories.feedback_repositories import ReviewSettingsRepository
from app.repositories.inbox_repositories import (
    ConversationNoteRepository,
    InboxSettingsRepository,
    QuickReplyLibraryRepository,
)
from app.repositories.knowledge_repositories import ScheduleExceptionRepository
from app.repositories.waitlist_repositories import WaitlistSettingsRepository
from app.schemas.constants.deposits import PaymentLinkKind
from app.schemas.domain.assistant_settings import AssistantSettingsDocument
from app.schemas.domain.campaigns import CampaignSettingsDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.customer_segments import CustomerSegmentDocument
from app.schemas.domain.customer_settings import CustomerSettingsDocument
from app.schemas.domain.deposits import (
    DepositSettingsDocument,
    PaymentLink,
    RetiredPaymentLink,
)
from app.schemas.domain.feedback import ReviewSettingsDocument
from app.schemas.domain.inbox_settings import InboxSettingsDocument
from app.schemas.domain.quick_replies import QuickReplyLibraryDocument
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.domain.waitlist import WaitlistSettingsDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.schemas.typings.deposits.constrained_strings import PaymentLinkLabel
from app.schemas.typings.deposits.strings import PaymentLinkHost, PaymentLinkPreview
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.use_cases.exports.setup_archive import SetupArchive
from tests.storage.document_evolution.sample_documents import sample_document

BUSINESS: BusinessId = BusinessId()
SEALED_ADDRESS: str = "sealed-payment-address-never-exported"
OTHER_BUSINESS: BusinessId = BusinessId()


def seeded[Document: BaseDocument](
    repository: type[BusinessScopedRepository[Document]],
    document_type: type[Document],
    collection: str,
) -> BusinessScopedRepository[Document]:
    """The collection with a document of the business and one of another."""

    stored = InMemoryDocumentCollectionAdapter(document_type)
    sample = sample_document(document_type, DocumentCollectionName(collection))
    for index, business_id in enumerate((BUSINESS, OTHER_BUSINESS)):
        document = sample.model_copy(update={"business_id": business_id})
        stored.upsert(f"{collection}-{index}", document)
    return repository(stored)


def setup_archive() -> SetupArchive:
    return SetupArchive(
        schedule_exception_repo=seeded(
            ScheduleExceptionRepository,
            ScheduleExceptionDocument,
            "schedule_exceptions",
        ),
        deposit_settings_repo=seeded(
            DepositSettingsRepository, DepositSettingsDocument, "deposit_settings"
        ),
        waitlist_settings_repo=seeded(
            WaitlistSettingsRepository, WaitlistSettingsDocument, "waitlist_settings"
        ),
        campaign_settings_repo=seeded(
            CampaignSettingsRepository, CampaignSettingsDocument, "campaign_settings"
        ),
        review_settings_repo=seeded(
            ReviewSettingsRepository, ReviewSettingsDocument, "review_settings"
        ),
        inbox_settings_repo=seeded(
            InboxSettingsRepository, InboxSettingsDocument, "inbox_settings"
        ),
        assistant_settings_repo=seeded(
            AssistantSettingsRepository,
            AssistantSettingsDocument,
            "assistant_settings",
        ),
        customer_settings_repo=seeded(
            CustomerSettingsRepository, CustomerSettingsDocument, "customer_settings"
        ),
        customer_segment_repo=seeded(
            CustomerSegmentRepository, CustomerSegmentDocument, "customer_segments"
        ),
        quick_reply_library_repo=seeded(
            QuickReplyLibraryRepository,
            QuickReplyLibraryDocument,
            "quick_reply_libraries",
        ),
        conversation_note_repo=seeded(
            ConversationNoteRepository, ConversationNoteDocument, "conversation_notes"
        ),
    )


def test_each_setup_file_holds_the_business_documents_only() -> None:
    pages = setup_archive().pages(BUSINESS)

    assert set(pages) == {
        "schedule_exceptions",
        "deposit_settings",
        "waitlist_settings",
        "campaign_settings",
        "review_settings",
        "inbox_settings",
        "assistant_settings",
        "customer_settings",
        "customer_segments",
        "quick_reply_libraries",
        "conversation_notes",
    }
    for name, file_pages in pages.items():
        documents = [document for page in file_pages for document in page]
        assert len(documents) == 1, name
        assert documents[0].model_dump()["business_id"] == BUSINESS, name


def test_a_payment_page_leaves_without_its_sealed_address() -> None:
    sample = sample_document(
        DepositSettingsDocument, DocumentCollectionName("deposit_settings")
    )
    link = PaymentLink(
        label=PaymentLinkLabel("Bank page"),
        kind=PaymentLinkKind.TEMPLATE,
        sealed_address=EncryptedChannelSecret(SEALED_ADDRESS),
        host=PaymentLinkHost("pay.example.it"),
        preview=PaymentLinkPreview("https://pay.example.it/…"),
        added_at=Microseconds(1),
    )
    stored = InMemoryDocumentCollectionAdapter(DepositSettingsDocument)
    stored.upsert(
        "deposits",
        sample.model_copy(
            update={
                "business_id": BUSINESS,
                "payment_links": [link],
                "retired_payment_links": [
                    RetiredPaymentLink(link=link, retired_at=Microseconds(2))
                ],
            }
        ),
    )
    archive = replace(
        setup_archive(), deposit_settings_repo=DepositSettingsRepository(stored)
    )

    [[exported]] = list(archive.pages(BUSINESS)["deposit_settings"])

    text = exported.model_dump_json()
    assert SEALED_ADDRESS not in text
    assert "pay.example.it" in text
