from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.config import ConfigContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.facilitators.referrals.referral_attribution_facilitator import (
    ReferralAttributionFacilitator,
)
from app.facilitators.referrals.referral_earnings_facilitator import (
    ReferralEarningsFacilitator,
)
from app.facilitators.referrals.referral_links_facilitator import (
    ReferralLinksFacilitator,
)


class ReferralFacilitatorsContainer(containers.DeclarativeContainer):
    """
    The referral program (migration 1150) as other contexts use it: links
    with a business's own code (the chat's and the table card's "Powered
    by", an owner's invitation), who brought a new business, and what its
    paid invoices earn (a partner's commission, an invitation's months). A
    child of FacilitatorsContainer, which names them flat
    (`facilitators.referral_links`).
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    referral_links: Singleton[ReferralLinksFacilitator] = Singleton(
        ReferralLinksFacilitator,
        referral_code_repo=repositories.referral_code_repo,
        cabinet_base_url=config.app_settings.provided.cabinet_base_url,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    referral_attribution: Singleton[ReferralAttributionFacilitator] = Singleton(
        ReferralAttributionFacilitator,
        referral_code_repo=repositories.referral_code_repo,
        referral_repo=repositories.referral_repo,
        partner_repo=repositories.partner_repo,
        business_repo=repositories.business_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    referral_earnings: Singleton[ReferralEarningsFacilitator] = Singleton(
        ReferralEarningsFacilitator,
        referral_repo=repositories.referral_repo,
        partner_repo=repositories.partner_repo,
        commission_entry_repo=repositories.commission_entry_repo,
        billing_credit_repo=repositories.billing_credit_repo,
        subscription_repo=repositories.subscription_repo,
        business_repo=repositories.business_repo,
        plan_registry=registries.plan_registry,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
