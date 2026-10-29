from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.brands import BrandDocument, BrandMember
from app.schemas.dto.brands.brand_commands import (
    BrandAccessRequest,
    ChangeBrandMemberCommand,
)
from app.schemas.dto.brands.brand_views import BrandView, BrandViewSource
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.use_cases.brands.brand_audit import BRAND_MEMBER_ENTITY, record_in_locations
from app.use_cases.brands.brand_rules import (
    assigned_locations,
    reached_locations,
    require_another_owner_stays,
)
from app.use_cases.brands.brand_view_loading import BrandViewLoader
from app.utilities.brands.brand_access import find_brand_member


class ChangeBrandMemberUseCase(UseCaseContract[ChangeBrandMemberCommand, BrandView]):
    """
    A brand owner changes a member's role or a manager's locations (after
    a fresh sign-in). The brand keeps at least one owner (ConflictError).
    The change is checked and stored in one step with what is stored, and
    each location the member gains or loses records it in its audit log;
    a location taken from a manager is closed to them at their next request.
    """

    def __init__(
        self,
        authorize_brand_access: UseCaseContract[BrandAccessRequest, BrandDocument],
        brand_repo: BrandRepoContract,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        audit_log_repo: AuditLogRepoContract,
        brand_view_transformer: TransformerContract[BrandViewSource, BrandView],
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
        self._views: BrandViewLoader = BrandViewLoader(
            business_repo, user_repo, brand_view_transformer
        )

    def run(self, input_data: ChangeBrandMemberCommand) -> BrandView:
        brand: BrandDocument = self._authorize_brand_access.run(
            BrandAccessRequest(
                user_id=input_data.user_id,
                brand_id=input_data.brand_id,
                required_role=BrandMemberRole.BRAND_OWNER,
            )
        )
        change = input_data.change
        location_ids: list[BusinessId] = [
            location.id for location in self._business_repo.list_by_brand(brand.id)
        ]
        assigned: list[BusinessId] = assigned_locations(
            change.role, change.business_ids, location_ids
        )
        self._step_up.require_recent_authentication()
        now: Microseconds = self._wall_clock.now_unix()
        before: list[BrandMember] = []

        def apply(current: BrandDocument) -> None:
            member: BrandMember | None = find_brand_member(
                current, input_data.member_user_id
            )
            if member is None:
                raise NotFoundError("This person is not on the brand's team.")

            if change.role is not BrandMemberRole.BRAND_OWNER:
                require_another_owner_stays(current, member.user_id)

            before.append(member.model_copy(deep=True))
            member.role = change.role
            member.business_ids = assigned
            current.updated_at = now

        updated: BrandDocument = self._brand_repo.update(brand.id, apply)
        previous: BrandMember = before[0]
        record_in_locations(
            self._audit_log_repo,
            [
                *reached_locations(previous.role, previous.business_ids, location_ids),
                *reached_locations(change.role, assigned, location_ids),
            ],
            input_data.user_id,
            AuditAction.UPDATE,
            BRAND_MEMBER_ENTITY,
            AuditEntityReference(str(input_data.member_user_id)),
            input_data.client_ip_address,
            now,
        )
        return self._views.load(updated, input_data.user_id)
