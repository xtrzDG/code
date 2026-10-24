from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.invoicing import InvoiceIssuingFacilitatorContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.phone_numbers import (
    PhoneLineLockRegistryContract,
    PhoneNumberCountryRegistryContract,
    PhoneNumberOfferSignerContract,
    PhoneNumberProvisionerAdapterContract,
    PhoneNumberRepoContract,
    PhoneNumberRequestRepoContract,
)
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
    UsageEventRepoContract,
)
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.storage import StorageScopeContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.billing_profiles import InvoiceLineText
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing_ledger import BillingNotice, InvoiceDescriptionInput
from app.schemas.dto.spend_guard import OwnerActionAdmission
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.conversations.strings import MessageText


@dataclass(frozen=True, slots=True, kw_only=True)
class PhoneNumberDependencies:
    """
    Everything the phone numbers context (W21-PHONE-NUMBERS, migration
    1213) takes from the rest of the application, as contracts: its two
    repositories and the ones of channels, versions, billing and the audit
    log, the carrier and the voice platform behind the provisioner, the
    phone line lock, the owner action limits, the cabinet's access and
    step-up checks, and the facilitators and settings it reads. The only
    place the dependency graph meets the typed root (the provider in
    app/containers/use_cases/phone_number_root_provider.py fills it).
    """

    authorize_business_access: UseCaseContract[BusinessAccessRequest, BusinessDocument]
    admit_owner_action: UseCaseContract[OwnerActionAdmission, None]
    check_owner_action_room: UseCaseContract[OwnerActionAdmission, None]
    step_up: StepUpGuardContract
    phone_number_repo: PhoneNumberRepoContract
    phone_number_request_repo: PhoneNumberRequestRepoContract
    channel_repo: ChannelRepoContract
    closure_repo: BusinessClosureRepoContract
    assistant_version_repo: AssistantVersionRepoContract
    audit_log_repo: AuditLogRepoContract
    business_repo: BusinessRepoContract
    subscription_repo: SubscriptionRepoContract
    invoice_repo: InvoiceRepoContract
    usage_event_repo: UsageEventRepoContract
    user_repo: UserRepoContract
    phone_number_provisioner: PhoneNumberProvisionerAdapterContract
    phone_number_country_registry: PhoneNumberCountryRegistryContract
    exchange_rate_registry: ExchangeRateRegistryContract
    plan_registry: PlanRegistryContract
    phone_line_lock: PhoneLineLockRegistryContract
    phone_number_parser: PhoneNumberParserContract
    offer_signer: PhoneNumberOfferSignerContract
    invoice_issuing: InvoiceIssuingFacilitatorContract
    manager_notifier: ManagerNotificationFacilitatorContract
    product_events: RecordProductEventFacilitatorContract
    invoice_description_transformer: TransformerContract[
        InvoiceDescriptionInput, InvoiceDescription
    ]
    invoice_line_texts_transformer: TransformerContract[
        InvoiceDescriptionInput, list[InvoiceLineText]
    ]
    billing_notice_transformer: TransformerContract[BillingNotice, MessageText]
    storage_scope: StorageScopeContract
    app_settings: AppSettings
    wall_clock: WallClock[Microseconds]
