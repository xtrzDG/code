from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.brands import BrandDocument, BrandMember
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.brands.brand_commands import CreateBrandCommand
from app.schemas.dto.brands.brand_views import BrandView, BrandViewSource
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.use_cases.brands.brand_audit import BRAND_LOCATION_ENTITY, record_in_locations
from app.use_cases.brands.brand_rules import (
    require_free_of_brands,
    require_own_business,
    require_valid_brand_name,
)
from app.use_cases.brands.brand_view_loading import BrandViewLoader
from app.use_cases.shared.team_two_factor import require_team_two_factors


class CreateBrandUseCase(UseCaseContract[CreateBrandCommand, BrandView]):
    """
    An owner makes one of their businesses the first location of a new
    brand and becomes the brand's owner. The business must be the
    person's own (they are one of its owners) and in no brand yet; it
    joins in one step with what is stored, so two brands never get it.
    The join is in the business's audit log. Making a business a brand's
    location is an owner's action in it, so its two-factor rule for its
    team applies (`mfa_required`).
    """

    def __init__(
        self,
        brand_repo: BrandRepoContract,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        audit_log_repo: AuditLogRepoContract,
        brand_view_transformer: TransformerContract[BrandViewSource, BrandView],
        session_assurance: SessionAssuranceContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._brand_repo: BrandRepoContract = brand_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._business_repo: BusinessRepoContract = business_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._views: BrandViewLoader = BrandViewLoader(
            business_repo, user_repo, brand_view_transformer
        )

    def run(self, input_data: CreateBrandCommand) -> BrandView:
        request = input_data.request
        require_valid_brand_name(request.name)
        business: BusinessDocument = require_own_business(
            self._business_repo.get(request.business_id),
            request.business_id,
            input_data.user_id,
        )
        require_free_of_brands(business)
        require_team_two_factors(
            self._session_assurance.current(), input_data.user_id, [business]
        )
        now: Microseconds = self._wall_clock.now_unix()
        brand = BrandDocument(
            name=request.name,
            members=[
                BrandMember(
                    user_id=input_data.user_id, role=BrandMemberRole.BRAND_OWNER
                )
            ],
            created_at=now,
            updated_at=now,
        )
        self._brand_repo.add(brand)

        def join(current: BusinessDocument) -> None:
            require_free_of_brands(current)
            current.brand_id = brand.id
            current.updated_at = now

        try:
            self._business_repo.update(business.id, join)
        except ConflictError:
            # Another brand took the business meanwhile: this one stays unborn.
            self._brand_repo.delete(brand.id)
            raise

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
