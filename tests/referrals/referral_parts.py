"""In-memory referral repositories and the real facilitators over them."""

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.client_care_repositories import (
    BillingCreditRepoContract,
)
from app.facilitators.referrals.referral_attribution_facilitator import (
    ReferralAttributionFacilitator,
)
from app.facilitators.referrals.referral_earnings_facilitator import (
    ReferralEarningsFacilitator,
)
from app.facilitators.referrals.referral_links_facilitator import (
    ReferralLinksFacilitator,
)
from app.repositories.commission_entry_repository import CommissionEntryRepository
from app.repositories.partner_repository import PartnerRepository
from app.repositories.referral_repositories import (
    ReferralCodeRepository,
    ReferralRepository,
)
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.referrals import (
    CommissionEntryDocument,
    ReferralCodeDocument,
    ReferralDocument,
)
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.utilities.storage.storage_scope_context import StorageScopeContext

CABINET_BASE_URL: CabinetBaseUrl = CabinetBaseUrl("https://app.example.test")


class ReferralRepositories:
    """The referral program's collections, in memory."""

    def __init__(self) -> None:
        self.partner_repo = PartnerRepository(
            InMemoryDocumentCollectionAdapter[PartnerDocument](PartnerDocument)
        )
        self.referral_code_repo = ReferralCodeRepository(
            InMemoryDocumentCollectionAdapter[ReferralCodeDocument](
                ReferralCodeDocument
            )
        )
        self.referral_repo = ReferralRepository(
            InMemoryDocumentCollectionAdapter[ReferralDocument](ReferralDocument)
        )
        self.commission_entry_repo = CommissionEntryRepository(
            InMemoryDocumentCollectionAdapter[CommissionEntryDocument](
                CommissionEntryDocument
            )
        )

    def links(
        self,
        wall_clock: WallClock[Microseconds],
        cabinet_base_url: CabinetBaseUrl | None = CABINET_BASE_URL,
    ) -> ReferralLinksFacilitator:
        return ReferralLinksFacilitator(
            referral_code_repo=self.referral_code_repo,
            cabinet_base_url=cabinet_base_url,
            wall_clock=wall_clock,
        )

    def attribution(
        self, business_repo: BusinessRepoContract, wall_clock: WallClock[Microseconds]
    ) -> ReferralAttributionFacilitator:
        return ReferralAttributionFacilitator(
            referral_code_repo=self.referral_code_repo,
            referral_repo=self.referral_repo,
            partner_repo=self.partner_repo,
            business_repo=business_repo,
            wall_clock=wall_clock,
        )

    def earnings(
        self,
        *,
        billing_credit_repo: BillingCreditRepoContract,
        subscription_repo: SubscriptionRepoContract,
        business_repo: BusinessRepoContract,
        plan_registry: PlanRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> ReferralEarningsFacilitator:
        return ReferralEarningsFacilitator(
            referral_repo=self.referral_repo,
            partner_repo=self.partner_repo,
            commission_entry_repo=self.commission_entry_repo,
            billing_credit_repo=billing_credit_repo,
            subscription_repo=subscription_repo,
            business_repo=business_repo,
            plan_registry=plan_registry,
            storage_scope=StorageScopeContext(),
            wall_clock=wall_clock,
        )
