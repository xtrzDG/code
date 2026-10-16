from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.domain.brands import BrandDocument
from app.schemas.dto.brands.brand_commands import (
    BrandAccessRequest,
    RemoveBrandLocationCommand,
)
from app.use_cases.brands.brand_departures import take_location_out


class RemoveBrandLocationUseCase(UseCaseContract[RemoveBrandLocationCommand, None]):
    """
    A brand owner takes a location out of the brand (after a fresh
    sign-in). The brand's team loses it at their next request; its own
    team and data stay (`take_location_out`).
    """

    def __init__(
        self,
        authorize_brand_access: UseCaseContract[BrandAccessRequest, BrandDocument],
        brand_repo: BrandRepoContract,
        business_repo: BusinessRepoContract,
        audit_log_repo: AuditLogRepoContract,
        step_up: StepUpGuardContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_brand_access: UseCaseContract[
            BrandAccessRequest, BrandDocument
        ] = authorize_brand_access
        self._brand_repo: BrandRepoContract = brand_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._step_up: StepUpGuardContract = step_up
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RemoveBrandLocationCommand) -> None:
        brand: BrandDocument = self._authorize_brand_access.run(
            BrandAccessRequest(
                user_id=input_data.user_id,
                brand_id=input_data.brand_id,
                required_role=BrandMemberRole.BRAND_OWNER,
            )
        )
        self._step_up.require_recent_authentication()
        take_location_out(
            self._business_repo,
            self._brand_repo,
            self._audit_log_repo,
            brand.id,
            input_data.location_id,
            input_data.user_id,
            input_data.client_ip_address,
            self._wall_clock.now_unix(),
        )
