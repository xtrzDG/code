from typed_time_provider import Microseconds

from app.contracts.billing import PackageUsageWarningRepoContract
from app.contracts.demo_data import DemoDatasetRegistryContract
from app.contracts.invoicing import (
    BillingProfileRepoContract,
    InvoiceIssuingFacilitatorContract,
)
from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
    UsageEventRepoContract,
)
from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
    UnansweredQuestionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.compliance_repositories import (
    AuditLogRepoContract,
    DpaAcceptanceRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    CallRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
    ReviewSettingsRepoContract,
)
from app.contracts.repositories.media_repositories import MessageMediaRepoContract
from app.contracts.repositories.topic_repositories import (
    ConversationTopicsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import DpaAcceptanceDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.demo_data import (
    DemoActivityRequest,
    DemoActivityStorage,
    DemoBusinessActivity,
)
from app.schemas.dto.media import MediaLocation, StoredMediaFile
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.demo.demo_channel_activity import stamp_demo_channels
from app.utilities.assembly.autotest_evaluation import build_verdict

# The owner accepted the DPA this long before the first version went live.
DPA_LEAD_MICROSECONDS: int = 2 * 60 * 60 * 1_000_000


class StoreDemoActivityUseCase(UseCaseContract[DemoActivityStorage, BusinessId]):
    """
    Last step of seeding a demo business: give the assembled versions their
    history (archived, published with a passed autotest run, a fresh
    draft), go live with the published one, and store the month of activity
    the demo catalog describes: customers, conversations with tool calls,
    phone calls, bookings, leads, handoffs, unanswered questions, feedback
    after visits, the subscription with its usage, the accepted DPA and
    audit entries, the voice notes and photos customers sent, the topics
    customers asked about, and when each channel last carried a message. A
    paid demo invoice gets its number and VAT as a payment gives them, with
    the business's billing details.
    """

    def __init__(
        self,
        demo_dataset_registry: DemoDatasetRegistryContract,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        call_repo: CallRepoContract,
        booking_repo: BookingRepoContract,
        lead_repo: LeadRepoContract,
        handoff_repo: HandoffRepoContract,
        unanswered_question_repo: UnansweredQuestionRepoContract,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        billing_profile_repo: BillingProfileRepoContract,
        invoice_issuing: InvoiceIssuingFacilitatorContract,
        usage_event_repo: UsageEventRepoContract,
        package_usage_warning_repo: PackageUsageWarningRepoContract,
        dpa_acceptance_repo: DpaAcceptanceRepoContract,
        audit_log_repo: AuditLogRepoContract,
        review_settings_repo: ReviewSettingsRepoContract,
        feedback_request_repo: FeedbackRequestRepoContract,
        message_media_repo: MessageMediaRepoContract,
        media_storage: MediaStorageAdapterContract,
        conversation_topics_repo: ConversationTopicsRepoContract,
        app_settings: AppSettings,
        channel_repo: ChannelRepoContract,
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._registry: DemoDatasetRegistryContract = demo_dataset_registry
        self._business_repo: BusinessRepoContract = business_repo
        self._version_repo: AssistantVersionRepoContract = assistant_version_repo
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._call_repo: CallRepoContract = call_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._question_repo: UnansweredQuestionRepoContract = unanswered_question_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._billing_profile_repo: BillingProfileRepoContract = billing_profile_repo
        self._invoice_issuing: InvoiceIssuingFacilitatorContract = invoice_issuing
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._warning_repo: PackageUsageWarningRepoContract = package_usage_warning_repo
        self._dpa_acceptance_repo: DpaAcceptanceRepoContract = dpa_acceptance_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._review_settings_repo: ReviewSettingsRepoContract = review_settings_repo
        self._feedback_request_repo: FeedbackRequestRepoContract = feedback_request_repo
        self._message_media_repo: MessageMediaRepoContract = message_media_repo
        self._media_storage: MediaStorageAdapterContract = media_storage
        self._topics_repo: ConversationTopicsRepoContract = conversation_topics_repo
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: DemoActivityStorage) -> BusinessId:
        business: BusinessDocument = input_data.foundation.business
        activity: DemoBusinessActivity = self._registry.build_activity(
            DemoActivityRequest(
                foundation=input_data.foundation,
                version_ids=input_data.version_ids,
                model_id=self._app_settings.llm_model_id,
                now=input_data.seeded_at,
            )
        )
        self._autotest_run_repo.save(activity.autotest_run)
        published_id: AssistantVersionId = self._record_version_history(
            input_data, activity.autotest_run
        )
        self._go_live(business.id, published_id, input_data.seeded_at)
        self._store_customers(activity)
        stamp_demo_channels(self._channel_repo, business.id, activity)
        self._store_feedback(activity)
        self._store_billing(business, activity)
        self._store_compliance(input_data, activity)
        return business.id

    def _record_version_history(
        self,
        input_data: DemoActivityStorage,
        autotest_run: AutotestRunDocument,
    ) -> AssistantVersionId:
        business_id: BusinessId = input_data.foundation.business.id
        published_id: AssistantVersionId | None = None
        for plan, version_id in zip(
            input_data.foundation.assistant_versions,
            input_data.version_ids,
            strict=True,
        ):
            version: AssistantVersionDocument | None = self._version_repo.get(
                business_id, version_id
            )
            if version is None:
                raise NotFoundError(f"Assistant version {version_id} was not found.")

            version.status = plan.status
            version.created_at = plan.created_at
            version.published_at = plan.published_at
            version.updated_at = plan.published_at or plan.created_at
            version.voice_agent_id = plan.voice_agent_id
            version.test_score = plan.test_score
            if plan.status is AssistantVersionStatus.PUBLISHED:
                published_id = version.id
                version.autotest_run_id = autotest_run.id
                version.test_score = autotest_run.average_score
                version.autotest_verdict = build_verdict(
                    autotest_run, autotest_run.updated_at
                )

            self._version_repo.save(version)

        if published_id is None:
            raise NotFoundError("The demo business has no published version.")

        return published_id

    def _go_live(
        self,
        business_id: BusinessId,
        published_id: AssistantVersionId,
        now: Microseconds,
    ) -> None:
        def publish(current: BusinessDocument) -> None:
            current.published_assistant_version_id = published_id
            current.updated_at = now

        self._business_repo.update(business_id, publish)

    def _store_customers(self, activity: DemoBusinessActivity) -> None:
        for contact in activity.contacts:
            self._contact_repo.save(contact)
        for conversation in activity.conversations:
            self._conversation_repo.save(conversation)
        for message in activity.messages:
            self._message_repo.save(message)
        for call in activity.calls:
            self._call_repo.save(call)
        for booking in activity.bookings:
            self._booking_repo.save(booking)
        for lead in activity.leads:
            self._lead_repo.save(lead)
        for handoff in activity.handoffs:
            self._handoff_repo.save(handoff)
        for question in activity.unanswered_questions:
            self._question_repo.save(question)
        for file in activity.media_files:
            self._media_storage.store(
                MediaLocation(
                    business_id=file.media.business_id, path=file.media.storage_path
                ),
                StoredMediaFile(content=file.content, media_type=file.media.media_type),
            )
            self._message_media_repo.save(file.media)
        if activity.conversation_topics is not None:
            self._topics_repo.save(activity.conversation_topics)

    def _store_feedback(self, activity: DemoBusinessActivity) -> None:
        if activity.review_settings is not None:
            self._review_settings_repo.save(activity.review_settings)
        for request in activity.feedback_requests:
            self._feedback_request_repo.insert_if_new(request)

    def _store_billing(
        self, business: BusinessDocument, activity: DemoBusinessActivity
    ) -> None:
        self._subscription_repo.save(activity.subscription)
        if activity.billing_profile is not None:
            self._billing_profile_repo.save(activity.billing_profile)
        for invoice in activity.invoices:
            self._invoice_repo.save(self._issue_if_paid(business, invoice))
        for event in activity.usage_events:
            self._usage_event_repo.append(event)
        for warning in activity.package_usage_warnings:
            self._warning_repo.save(warning)

    def _issue_if_paid(
        self, business: BusinessDocument, invoice: InvoiceDocument
    ) -> InvoiceDocument:
        if invoice.status is not InvoiceStatus.PAID:
            return invoice

        charged = Money(
            amount_minor=invoice.amount_minor, currency_code=invoice.currency_code
        )
        return self._invoice_issuing.issue(business, invoice, charged=charged)

    def _store_compliance(
        self,
        input_data: DemoActivityStorage,
        activity: DemoBusinessActivity,
    ) -> None:
        business: BusinessDocument = input_data.foundation.business
        first_live: Microseconds = min(
            plan.published_at
            for plan in input_data.foundation.assistant_versions
            if plan.published_at is not None
        )
        accepted_at = Microseconds(int(first_live) - DPA_LEAD_MICROSECONDS)
        self._dpa_acceptance_repo.save(
            DpaAcceptanceDocument(
                business_id=business.id,
                document_version=self._app_settings.dpa_document_version,
                accepted_by=next(
                    member.user_id
                    for member in business.members
                    if member.role is BusinessMemberRole.OWNER
                ),
                accepted_at=accepted_at,
                created_at=accepted_at,
                updated_at=accepted_at,
            )
        )
        for entry in activity.audit_log_entries:
            self._audit_log_repo.append(entry)
