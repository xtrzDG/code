from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import (
    SessionAssuranceContract,
    StepUpGuardContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.brands import BrandDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.brands.brand_commands import (
    AddBrandLocationCommand,
    BrandAccessRequest,
)
from app.schemas.dto.brands.brand_views import BrandView, BrandViewSource
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.use_cases.brands.brand_audit import BRAND_LOCATION_ENTITY, record_in_locations
from app.use_cases.brands.brand_rules import (
    require_free_of_brands,
    require_own_business,
)
from app.use_cases.brands.brand_view_loading import BrandViewLoader
from app.use_cases.shared.team_two_factor import require_team_two_factors


class AddBrandLocationUseCase(UseCaseContract[AddBrandLocationCommand, BrandView]):
    """
    A brand owner brings one of their own businesses into the brand (after
    a fresh sign-in): its team stays, and the brand's team reaches it from
    now on (its owners as owners; managers only once assigned to it). The
    business must be in no brand; the join is one step with what is stored
    and shows in the business's audit log. Joining is an owner's action in
    the business, so its own two-factor rule for its team applies too
    (`mfa_required`), besides the brand's locations' (the brand check).
    """

    def __init__(
        self,
        authorize_brand_access: UseCaseContract[BrandAccessRequest, BrandDocument],
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        audit_log_repo: AuditLogRepoContract,
        brand_view_transformer: TransformerContract[BrandViewSource, BrandView],
        step_up: StepUpGuardContract,
        session_assurance: SessionAssuranceContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_brand_access: UseCaseContract[
            BrandAccessRequest, BrandDocument
        ] = authorize_brand_access
        self._business_repo: BusinessRepoContract = business_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._step_up: StepUpGuardContract = step_up
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._views: BrandViewLoader = BrandViewLoader(
            business_repo, user_repo, brand_view_transformer
        )

    def run(self, input_data: AddBrandLocationCommand) -> BrandView:
        brand: BrandDocument = self._authorize_brand_access.run(
            BrandAccessRequest(
                user_id=input_data.user_id,
                brand_id=input_data.brand_id,
                required_role=BrandMemberRole.BRAND_OWNER,
            )
        )
        business_id = input_data.request.business_id
        business: BusinessDocument = require_own_business(
            self._business_repo.get(business_id), business_id, input_data.user_id
        )
        require_free_of_brands(business)
        require_team_two_factors(
            self._session_assurance.current(), input_data.user_id, [business]
        )
        self._step_up.require_recent_authentication()
        now: Microseconds = self._wall_clock.now_unix()

        def join(current: BusinessDocument) -> None:
            require_free_of_brands(current)
            current.brand_id = brand.id
            current.updated_at = now

        self._business_repo.update(business.id, join)
        record_in_locations(
            self._audit_log_repo,
            [business.id],
            input_data.user_id,
            AuditAction.CREATE,
            BRAND_LOCATION_ENTITY,
            AuditEntityReference(str(brand.id)),
            input_data.client_ip_address,
            now,
        )
        return self._views.load(brand, input_data.user_id)
