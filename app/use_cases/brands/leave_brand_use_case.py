from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.brands.brand_commands import LeaveBrandCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.brands.brand_departures import take_location_out


class LeaveBrandUseCase(UseCaseContract[LeaveBrandCommand, None]):
    """
    An owner of a location takes it out of its brand (after a fresh
    sign-in): the location's own owners never depend on the brand's team
    to end its access. NotFoundError when the business has no brand.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        brand_repo: BrandRepoContract,
        business_repo: BusinessRepoContract,
        audit_log_repo: AuditLogRepoContract,
        step_up: StepUpGuardContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._brand_repo: BrandRepoContract = brand_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._step_up: StepUpGuardContract = step_up
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: LeaveBrandCommand) -> None:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        if business.brand_id is None:
            raise NotFoundError("This business is no location of a brand.")

        self._step_up.require_recent_authentication()
        take_location_out(
            self._business_repo,
            self._brand_repo,
            self._audit_log_repo,
            business.brand_id,
            business.id,
            input_data.user_id,
            input_data.client_ip_address,
            self._wall_clock.now_unix(),
        )
