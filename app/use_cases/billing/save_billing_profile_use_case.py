from typed_time_provider import Microseconds, WallClock

from app.contracts.invoicing import (
    BillingProfileRepoContract,
    TaxPolicyRegistryContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing_profiles import BillingProfileDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing_profiles import (
    BillingProfileRequest,
    BillingProfileView,
    SaveBillingProfileCommand,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.billing.billing_profile_views import view_billing_profile
from app.utilities.billing.invoicing_keys import derive_billing_profile_id
from app.utilities.localization.cldr_language_names import (
    get_english_locale,
    read_locale_name,
)

BILLING_PROFILE_ENTITY: AuditEntityName = AuditEntityName("billing_profile")


class SaveBillingProfileUseCase(
    UseCaseContract[SaveBillingProfileCommand, BillingProfileView]
):
    """
    An owner saves the billing details the next invoices will print: the
    registered name, the tax number, the address, the e-mail invoices and
    receipts go to, and the country (it decides the VAT). Invoices already
    issued keep the details they were issued with. A sole trader's details
    are personal data, so every save is audited (with the address it came
    from).

    Raises:
        ValidationFailedError: the country is not a known one.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        billing_profile_repo: BillingProfileRepoContract,
        tax_policy_registry: TaxPolicyRegistryContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._billing_profile_repo: BillingProfileRepoContract = billing_profile_repo
        self._tax_policy_registry: TaxPolicyRegistryContract = tax_policy_registry
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SaveBillingProfileCommand) -> BillingProfileView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        request: BillingProfileRequest = input_data.request
        if (
            read_locale_name(
                get_english_locale().territories, str(request.country_code)
            )
            is None
        ):
            raise ValidationFailedError(
                f"Unknown country {request.country_code} in the billing details."
            )

        now: Microseconds = self._wall_clock.now_unix()
        stored: BillingProfileDocument | None = (
            self._billing_profile_repo.get_by_business(business.id)
        )
        profile = BillingProfileDocument(
            id=derive_billing_profile_id(business.id),
            business_id=business.id,
            legal_name=request.legal_name,
            tax_id=request.tax_id,
            address=request.address,
            billing_email=request.billing_email,
            country_code=request.country_code,
            updated_by=input_data.user_id,
            created_at=now if stored is None else stored.created_at,
            updated_at=now,
        )
        self._billing_profile_repo.save(profile)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=BILLING_PROFILE_ENTITY,
                entity_id=AuditEntityReference(str(profile.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return view_billing_profile(business, profile, self._tax_policy_registry)
