"""
A Georgian client on its free trial (set up by the platform team) in the
billing testbed, platform admins of each role, and the account actions,
notes and timeline wired over the same in-memory storage.
"""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.analytics_repositories import ProductEventRepository
from app.repositories.client_care_repositories import (
    ClientHealthChangeRepository,
    ClientNoteRepository,
)
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.client_health_changes import ClientHealthChangeDocument
from app.schemas.domain.client_notes import ClientNoteDocument
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.access.constrained_strings import AdminActionReason
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.use_cases.admin.billing_actions.account_action_gate import AccountActionGate
from app.use_cases.admin.billing_actions.complete_onboarding_use_case import (
    CompleteOnboardingUseCase,
)
from app.use_cases.admin.billing_actions.extend_trial_use_case import (
    ExtendTrialUseCase,
)
from app.use_cases.admin.billing_actions.give_discount_use_case import (
    GiveDiscountUseCase,
)
from app.use_cases.admin.billing_actions.grant_credit_use_case import (
    GrantCreditUseCase,
)
from app.use_cases.admin.billing_actions.mark_invoice_paid_use_case import (
    MarkInvoicePaidUseCase,
)
from app.use_cases.admin.billing_actions.override_plan_use_case import (
    OverridePlanUseCase,
)
from app.use_cases.admin.billing_actions.waive_setup_fee_use_case import (
    WaiveSetupFeeUseCase,
)
from app.use_cases.admin.client_notes.client_note_board import ClientNoteBoard
from app.use_cases.admin.timeline.get_client_timeline_use_case import (
    GetClientTimelineUseCase,
)
from tests.admin_actions.role_authorizer import RoleAuthorizer
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.grace_steps import start_trial
from tests.foundation.access_support import AllowStepUp

REASON: AdminActionReason = AdminActionReason("Closing the deal after the demo call")
ADMIN_IP: ClientIpAddress = ClientIpAddress("198.51.100.7")


class ActionWorld:
    """One client on trial, a SUPER, a BILLING and a SUPPORT admin."""

    def __init__(self) -> None:
        testbed = self.testbed = BillingTestbed()
        self.owner, self.business = start_trial(testbed)
        self.authorize = RoleAuthorizer(testbed.user_repo)
        self.founder = self.add_admin("Nino", PlatformAdminRole.SUPER)
        self.accountant = self.add_admin("Levan", PlatformAdminRole.BILLING)
        self.support = self.add_admin("Tamar", PlatformAdminRole.SUPPORT_READONLY)
        clock = testbed.clock.wall_clock
        gate = AccountActionGate(
            self.authorize,
            testbed.business_repo,
            testbed.subscription_repo,
            testbed.audit_log_repo,
            AllowStepUp(),
        )
        self.extend_trial = ExtendTrialUseCase(
            gate,
            testbed.subscription_repo,
            testbed.invoice_repo,
            testbed.business_repo,
            clock,
        )
        self.give_discount = GiveDiscountUseCase(gate, testbed.subscription_repo, clock)
        self.grant_credit = GrantCreditUseCase(gate, testbed.billing_credit_repo, clock)
        self.waive_setup_fee = WaiveSetupFeeUseCase(
            gate, testbed.subscription_repo, testbed.invoice_repo, clock
        )
        self.mark_invoice_paid = MarkInvoicePaidUseCase(
            gate,
            testbed.subscription_repo,
            testbed.invoice_repo,
            testbed.business_repo,
            testbed.product_events,
            clock,
            testbed.referral_earnings,
        )
        self.override_plan = OverridePlanUseCase(
            gate,
            testbed.subscription_repo,
            testbed.invoice_repo,
            testbed.business_repo,
            testbed.plan_registry,
            testbed.payment_gateway,
            testbed.voice_agent_removals,
            testbed.product_events,
            clock,
        )
        self.complete_onboarding = CompleteOnboardingUseCase(
            self.authorize,
            testbed.business_repo,
            testbed.onboarding_request_repo,
            testbed.audit_log_repo,
            clock,
        )
        self.note_repo = ClientNoteRepository(
            InMemoryDocumentCollectionAdapter(ClientNoteDocument)
        )
        self.note_board = ClientNoteBoard(
            self.authorize, testbed.business_repo, self.note_repo, testbed.user_repo
        )
        self.health_repo = ClientHealthChangeRepository(
            InMemoryDocumentCollectionAdapter(ClientHealthChangeDocument)
        )
        self.product_event_repo = ProductEventRepository(
            InMemoryDocumentCollectionAdapter(ProductEventDocument)
        )
        self.timeline = GetClientTimelineUseCase(
            self.authorize,
            testbed.business_repo,
            testbed.audit_log_repo,
            testbed.invoice_repo,
            testbed.billing_credit_repo,
            self.product_event_repo,
            self.health_repo,
            testbed.onboarding_request_repo,
            testbed.user_repo,
        )

    def add_admin(self, name: str, role: PlatformAdminRole) -> UserDocument:
        admin = self.testbed.add_user(
            email=f"{name.lower()}@platform.example",
            display_name=name,
            is_platform_admin=True,
        )
        self.authorize.roles[admin.id] = role
        return admin

    def client(self) -> BusinessDocument:
        return self.testbed.business(self.business.id)
