"""
The subscription lifecycle over the billing testbed: an owner with a paid
monthly subscription (trial, checkout, trial end), and the lifecycle use
cases wired over the same in-memory storage, clock and Flitt sandbox.
"""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.billing.owner_win_back_facilitator import (
    OwnerWinBackFacilitator,
)
from app.registries.billing.subscription_lifecycle_policy_registry import (
    SubscriptionLifecyclePolicyRegistry,
)
from app.repositories.conversation_repositories import ConversationRepository
from app.schemas.constants.billing import PlanKey
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import (
    BillingOverviewSource,
    StartTrialCommand,
    StartTrialRequest,
)
from app.schemas.dto.subscription_lifecycle import SubscriptionLifecycleView
from app.schemas.typings.platform.strings import PlatformSecret
from app.use_cases.billing.lifecycle.accept_retention_offer_use_case import (
    AcceptRetentionOfferUseCase,
)
from app.use_cases.billing.lifecycle.assemble_subscription_lifecycle_use_case import (
    AssembleSubscriptionLifecycleUseCase,
)
from app.use_cases.billing.lifecycle.get_subscription_lifecycle_use_case import (
    GetSubscriptionLifecycleUseCase,
)
from app.use_cases.billing.lifecycle.pause_subscription_use_case import (
    PauseSubscriptionUseCase,
)
from app.use_cases.billing.lifecycle.resume_subscription_use_case import (
    ResumeSubscriptionUseCase,
)
from app.use_cases.billing.lifecycle.run_subscription_pauses_use_case import (
    RunSubscriptionPausesUseCase,
)
from app.use_cases.billing.lifecycle.send_win_back_messages_use_case import (
    SendWinBackMessagesUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from tests.billing.billing_settings import GEORGIA, CountryPreset
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.grace_steps import end_trial, pay_open_invoices
from tests.subscription_lifecycle.lifecycle_settings import lifecycle_settings

TRIAL_DAYS: int = 14


class LifecycleWorld(BillingTestbed):
    """Every billing use case plus the lifecycle ones, over one storage."""

    def __init__(self, is_pause_enabled: bool = True) -> None:
        super().__init__(settings=lifecycle_settings(is_pause_enabled))
        resolver = LocalizedTextResolver()
        authorize = self.authorize
        self.policy_registry = SubscriptionLifecyclePolicyRegistry()
        self.conversation_repo = ConversationRepository(
            InMemoryDocumentCollectionAdapter[ConversationDocument](
                ConversationDocument
            )
        )
        self.assemble_lifecycle = AssembleSubscriptionLifecycleUseCase(
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            subscription_event_repo=self.subscription_event_repo,
            billing_credit_repo=self.billing_credit_repo,
            plan_registry=self.plan_registry,
            lifecycle_policy_registry=self.policy_registry,
            localized_text_resolver=resolver,
            app_settings=self.settings,
        )
        self.get_lifecycle = GetSubscriptionLifecycleUseCase(
            authorize_business_access=authorize,
            assemble_subscription_lifecycle=self.assemble_lifecycle,
        )
        self.pause = PauseSubscriptionUseCase(
            authorize_business_access=authorize,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            subscription_event_repo=self.subscription_event_repo,
            payment_gateway=self.payment_gateway,
            lifecycle_policy_registry=self.policy_registry,
            app_settings=self.settings,
            assemble_billing_overview=self.assemble_overview,
            wall_clock=self.clock.wall_clock,
        )
        self.resume = ResumeSubscriptionUseCase(
            authorize_business_access=authorize,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            business_repo=self.business_repo,
            subscription_event_repo=self.subscription_event_repo,
            payment_gateway=self.payment_gateway,
            assemble_billing_overview=self.assemble_overview,
            wall_clock=self.clock.wall_clock,
        )
        self.accept_offer = AcceptRetentionOfferUseCase(
            authorize_business_access=authorize,
            assemble_subscription_lifecycle=self.assemble_lifecycle,
            pause_subscription=self.pause,
            change_plan=self.change_plan,
            assemble_billing_overview=self.assemble_overview,
            subscription_repo=self.subscription_repo,
            billing_credit_repo=self.billing_credit_repo,
            subscription_event_repo=self.subscription_event_repo,
            wall_clock=self.clock.wall_clock,
        )
        self.run_pauses = RunSubscriptionPausesUseCase(
            business_repo=self.business_repo,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            subscription_event_repo=self.subscription_event_repo,
            user_repo=self.user_repo,
            issue_due_invoices=self.issue_due_invoices,
            lifecycle_policy_registry=self.policy_registry,
            manager_notifier=self.notifier,
            billing_notice_transformer=self.notice_transformer,
            wall_clock=self.clock.wall_clock,
        )
        self.send_win_back = SendWinBackMessagesUseCase(
            business_repo=self.business_repo,
            subscription_repo=self.subscription_repo,
            subscription_event_repo=self.subscription_event_repo,
            conversation_repo=self.conversation_repo,
            lifecycle_policy_registry=self.policy_registry,
            owner_win_back=OwnerWinBackFacilitator(
                user_repo=self.user_repo,
                manager_notifier=self.notifier,
                link_signer=StaffLinkSigner(PlatformSecret("test-link-key-0000")),
                localized_text_resolver=resolver,
                app_settings=self.settings,
                wall_clock=self.clock.wall_clock,
            ),
            wall_clock=self.clock.wall_clock,
        )

    def paying_business(
        self,
        country: CountryPreset = GEORGIA,
        plan_key: PlanKey = PlanKey.VOICE_AND_CHAT,
        email: str = "owner@example.com",
    ) -> tuple[UserDocument, BusinessDocument]:
        """
        An owner (signed in by e-mail) whose monthly subscription is paid,
        automatic charges on: the trial paid ahead, then the trial ended, so
        the first paid month runs. Set up in the cabinet: no setup fee.
        """

        owner = self.add_user(email=email, locale="en", display_name="Nino")
        business = self.add_business(owner, country, plan_key=plan_key)
        self.start_trial.run(
            StartTrialCommand(
                user_id=owner.id, business_id=business.id, request=StartTrialRequest()
            )
        )
        pay_open_invoices(self, owner, business)
        self.clock.advance(days=TRIAL_DAYS, hours=1)
        end_trial(self)
        return owner, business

    def trialing_business(self) -> tuple[UserDocument, BusinessDocument]:
        owner = self.add_user(email="trial@example.com", locale="en")
        business = self.add_business(owner, GEORGIA, name="Khachapuri House")
        self.start_trial.run(
            StartTrialCommand(
                user_id=owner.id, business_id=business.id, request=StartTrialRequest()
            )
        )
        return owner, business

    def current(self, business: BusinessDocument) -> SubscriptionDocument:
        return self.subscription(business.id)

    def run_pause_job(self) -> int:
        return self.run_job(self.run_pauses, "run_subscription_pauses")

    def run_win_back_job(self) -> int:
        return self.run_job(self.send_win_back, "send_win_back_messages")

    def steps(self, business: BusinessDocument) -> list[SubscriptionEventDocument]:
        return self.subscription_event_repo.list_by_business(business.id)

    def lifecycle_of(self, business: BusinessDocument) -> SubscriptionLifecycleView:
        return self.assemble_lifecycle.run(BillingOverviewSource(business=business))

    def open_invoices_of(self, business: BusinessDocument) -> list[InvoiceDocument]:
        return [
            invoice
            for invoice in self.invoices(business.id)
            if invoice.status.value in {"issued", "failed"}
        ]
