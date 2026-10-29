from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.brands import BrandDocument, BrandMember
from app.schemas.dto.brands.brand_commands import (
    BrandAccessRequest,
    RemoveBrandMemberCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.use_cases.brands.brand_audit import BRAND_MEMBER_ENTITY, record_in_locations
from app.use_cases.brands.brand_rules import (
    reached_locations,
    require_another_owner_stays,
)
from app.utilities.brands.brand_access import find_brand_member


class RemoveBrandMemberUseCase(UseCaseContract[RemoveBrandMemberCommand, None]):
    """
    A brand owner takes a person off the brand's team, or a member leaves
    it (after a fresh sign-in); the brand keeps at least one owner
    (ConflictError). Every location the person reached through the brand
    is closed to them at their next request (their own memberships of a
    location stay) and records it in its audit log.
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

    def run(self, input_data: RemoveBrandMemberCommand) -> None:
        is_leaving: bool = input_data.member_user_id == input_data.user_id
        brand: BrandDocument = self._authorize_brand_access.run(
            BrandAccessRequest(
                user_id=input_data.user_id,
                brand_id=input_data.brand_id,
                required_role=None if is_leaving else BrandMemberRole.BRAND_OWNER,
            )
        )
        self._step_up.require_recent_authentication()
        location_ids: list[BusinessId] = [
            location.id for location in self._business_repo.list_by_brand(brand.id)
        ]
        now: Microseconds = self._wall_clock.now_unix()
        removed: list[BrandMember] = []

        def remove(current: BrandDocument) -> None:
            member: BrandMember | None = find_brand_member(
                current, input_data.member_user_id
            )
            if member is None:
                raise NotFoundError("This person is not on the brand's team.")

            require_another_owner_stays(current, member.user_id)
            removed.append(member)
            current.members = [
                other for other in current.members if other.user_id != member.user_id
            ]
            current.updated_at = now

        self._brand_repo.update(brand.id, remove)
        record_in_locations(
            self._audit_log_repo,
            reached_locations(removed[0].role, removed[0].business_ids, location_ids),
            input_data.user_id,
            AuditAction.DELETE,
            BRAND_MEMBER_ENTITY,
            AuditEntityReference(str(input_data.member_user_id)),
            input_data.client_ip_address,
            now,
        )
