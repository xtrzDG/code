from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.invoicing import InvoiceIssuingFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.payment_methods import PaymentRetryRepoContract
from app.contracts.referrals import ReferralEarningsFacilitatorContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing_ledger import (
    BillingNotice,
    DueInvoicesRequest,
    InvoiceDescriptionInput,
)
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.conversations.strings import MessageText


@dataclass(frozen=True, slots=True, kw_only=True)
class PaymentDependencies:
    """
    Everything the payments context (R17-PAYMENTS-REGIONAL, migration 1214)
    takes from the rest of the application, as contracts: the repositories
    of subscriptions, invoices, payment orders and retries, the payment
    gateway (Flitt or Stripe, each behind its circuit), the cabinet's access
    check, the issuing of due invoices and the facilitators and settings it
    reads. The only place the dependency graph meets the typed root (the
    provider in app/containers/use_cases/payment_root_provider.py fills it).
    """

    authorize_business_access: UseCaseContract[BusinessAccessRequest, BusinessDocument]
    issue_due_invoices: UseCaseContract[DueInvoicesRequest, list[InvoiceDocument]]
    subscription_repo: SubscriptionRepoContract
    invoice_repo: InvoiceRepoContract
    payment_order_repo: PaymentOrderRepoContract
    payment_retry_repo: PaymentRetryRepoContract
    business_repo: BusinessRepoContract
    brand_repo: BrandRepoContract
    user_repo: UserRepoContract
    payment_gateway: PaymentGatewayAdapterContract
    plan_registry: PlanRegistryContract
    invoice_issuing: InvoiceIssuingFacilitatorContract
    manager_notifier: ManagerNotificationFacilitatorContract
    link_signer: StaffLinkSignerContract
    referral_earnings: ReferralEarningsFacilitatorContract
    product_events: RecordProductEventFacilitatorContract
    secret_cipher: SecretCipherAdapterContract
    localized_text_resolver: LocalizedTextResolverContract
    billing_notice_transformer: TransformerContract[BillingNotice, MessageText]
    invoice_description_transformer: TransformerContract[
        InvoiceDescriptionInput, InvoiceDescription
    ]
    app_settings: AppSettings
    wall_clock: WallClock[Microseconds]
