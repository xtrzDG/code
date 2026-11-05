from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.referrals.partner_admin import (
    AddPartnerCodeCommand,
    AdminPartnersQuery,
    CreatePartnerCommand,
    MarkPayoutPaidCommand,
    PartnerAdminView,
    PartnerList,
    PayoutReceipt,
    PayoutReportQuery,
    PayoutReportView,
    UpdatePartnerCommand,
)
from app.schemas.dto.referrals.partner_portal import (
    CommissionEntryPage,
    PartnerPageQuery,
    PartnerPortalQuery,
    PartnerPortalView,
    PartnerReferralPage,
)
from app.schemas.dto.referrals.program import (
    PoweredByCommand,
    PoweredByView,
    ReferralProgramQuery,
    ReferralProgramView,
)
from app.use_cases.referrals.partner_summaries import PartnerReaders
from app.use_cases.referrals.partners.add_partner_code_use_case import (
    AddPartnerCodeUseCase,
)
from app.use_cases.referrals.partners.create_partner_use_case import (
    CreatePartnerUseCase,
)
from app.use_cases.referrals.partners.get_payout_report_use_case import (
    GetPayoutReportUseCase,
)
from app.use_cases.referrals.partners.list_partners_use_case import ListPartnersUseCase
from app.use_cases.referrals.partners.mark_payout_paid_use_case import (
    MarkPayoutPaidUseCase,
)
from app.use_cases.referrals.partners.partner_admin_gate import PartnerAdminGate
from app.use_cases.referrals.partners.update_partner_use_case import (
    UpdatePartnerUseCase,
)
from app.use_cases.referrals.portal.get_partner_portal_use_case import (
    GetPartnerPortalUseCase,
)
from app.use_cases.referrals.portal.list_partner_commissions_use_case import (
    ListPartnerCommissionsUseCase,
)
from app.use_cases.referrals.portal.list_partner_referrals_use_case import (
    ListPartnerReferralsUseCase,
)
from app.use_cases.referrals.program.get_referral_program_use_case import (
    GetReferralProgramUseCase,
)
from app.use_cases.referrals.program.set_powered_by_use_case import SetPoweredByUseCase


class ReferralUseCasesContainer(containers.DeclarativeContainer):
    """
    The referral and partner program (migration 1150): an owner's
    invitation and "Powered by" link, a partner's portal, and the platform
    team's partners and payouts.
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    platform_use_cases: PlatformUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    authorize = account_use_cases.authorize_business_access_use_case
    wall_clock = time_provider.microsecond_wall_clock
    readers: Factory[PartnerReaders] = Factory(
        PartnerReaders,
        referral_code_repo=repositories.referral_code_repo,
        referral_repo=repositories.referral_repo,
        commission_entry_repo=repositories.commission_entry_repo,
        cabinet_base_url=config.app_settings.provided.cabinet_base_url,
    )
    admin_gate: Factory[PartnerAdminGate] = Factory(
        PartnerAdminGate,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        partner_repo=repositories.partner_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )

    get_referral_program_use_case: Factory[
        UseCaseContract[ReferralProgramQuery, ReferralProgramView]
    ] = Factory(
        GetReferralProgramUseCase,
        authorize_business_access=authorize,
        referral_repo=repositories.referral_repo,
        booking_repo=repositories.booking_repo,
        referral_links=facilitators.referral_links,
        wall_clock=wall_clock,
    )
    set_powered_by_use_case: Factory[
        UseCaseContract[PoweredByCommand, PoweredByView]
    ] = Factory(
        SetPoweredByUseCase,
        authorize_business_access=authorize,
        business_repo=repositories.business_repo,
        referral_links=facilitators.referral_links,
        wall_clock=wall_clock,
    )
    get_partner_portal_use_case: Factory[
        UseCaseContract[PartnerPortalQuery, PartnerPortalView]
    ] = Factory(
        GetPartnerPortalUseCase,
        user_repo=repositories.user_repo,
        partner_repo=repositories.partner_repo,
        readers=readers,
    )
    list_partner_referrals_use_case: Factory[
        UseCaseContract[PartnerPageQuery, PartnerReferralPage]
    ] = Factory(
        ListPartnerReferralsUseCase,
        user_repo=repositories.user_repo,
        partner_repo=repositories.partner_repo,
        referral_repo=repositories.referral_repo,
        business_repo=repositories.business_repo,
    )
    list_partner_commissions_use_case: Factory[
        UseCaseContract[PartnerPageQuery, CommissionEntryPage]
    ] = Factory(
        ListPartnerCommissionsUseCase,
        user_repo=repositories.user_repo,
        partner_repo=repositories.partner_repo,
        commission_entry_repo=repositories.commission_entry_repo,
        business_repo=repositories.business_repo,
    )
    list_partners_use_case: Factory[
        UseCaseContract[AdminPartnersQuery, PartnerList]
    ] = Factory(
        ListPartnersUseCase,
        gate=admin_gate,
        partner_repo=repositories.partner_repo,
        readers=readers,
    )
    create_partner_use_case: Factory[
        UseCaseContract[CreatePartnerCommand, PartnerAdminView]
    ] = Factory(
        CreatePartnerUseCase,
        gate=admin_gate,
        partner_repo=repositories.partner_repo,
        referral_code_repo=repositories.referral_code_repo,
        phone_number_parser=utilities.phone_number_parser,
        readers=readers,
    )
    update_partner_use_case: Factory[
        UseCaseContract[UpdatePartnerCommand, PartnerAdminView]
    ] = Factory(
        UpdatePartnerUseCase,
        gate=admin_gate,
        partner_repo=repositories.partner_repo,
        readers=readers,
    )
    add_partner_code_use_case: Factory[
        UseCaseContract[AddPartnerCodeCommand, PartnerAdminView]
    ] = Factory(
        AddPartnerCodeUseCase,
        gate=admin_gate,
        referral_code_repo=repositories.referral_code_repo,
        readers=readers,
    )
    get_payout_report_use_case: Factory[
        UseCaseContract[PayoutReportQuery, PayoutReportView]
    ] = Factory(
        GetPayoutReportUseCase,
        gate=admin_gate,
        partner_repo=repositories.partner_repo,
        commission_entry_repo=repositories.commission_entry_repo,
    )
    mark_payout_paid_use_case: Factory[
        UseCaseContract[MarkPayoutPaidCommand, PayoutReceipt]
    ] = Factory(
        MarkPayoutPaidUseCase,
        gate=admin_gate,
        commission_entry_repo=repositories.commission_entry_repo,
    )
