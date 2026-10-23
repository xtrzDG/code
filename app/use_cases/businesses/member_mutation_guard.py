from collections.abc import Callable
from typing import Protocol

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.businesses import BusinessView, BusinessViewSource
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.businesses.business_view_sources import business_view_source

# Changes one member on the business as stored now; False when it changes
# nothing (the member already has what was asked).
type MemberChange = Callable[[BusinessDocument, BusinessMember], bool]


class MemberCommand(Protocol):
    """What every command on one member of the team carries."""

    @property
    def user_id(self) -> UserId: ...

    @property
    def business_id(self) -> BusinessId: ...

    @property
    def member_user_id(self) -> UserId: ...

    @property
    def client_ip_address(self) -> ClientIpAddress | None: ...


class MemberMutationGuard:
    """
    Every change to one member of a business's team goes through here
    (changing a role, removing a member): only an owner who signed in
    recently may make it, the member must belong to the business, and the
    business keeps at least one owner afterwards. The change is made on the
    business as stored now, so a change saved meanwhile (settings, another
    member) is kept, and a real change is audited. An owner whose own
    ownership was the access is checked again on the stored business: one
    removed or demoted meanwhile changes nothing.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        brand_repo: BrandRepoContract,
        audit_log_repo: AuditLogRepoContract,
        business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ],
        wall_clock: WallClock[Microseconds],
        step_up: StepUpGuardContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._business_repo: BusinessRepoContract = business_repo
        self._user_repo: UserRepoContract = user_repo
        self._brand_repo: BrandRepoContract = brand_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ] = business_view_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._step_up: StepUpGuardContract = step_up

    def apply(
        self,
        command: MemberCommand,
        change: MemberChange,
        action: AuditAction,
    ) -> BusinessView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=command.user_id,
                business_id=command.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        self._step_up.require_recent_authentication()
        # A brand owner is not on the team; their access is the brand's.
        owner_by_membership: bool = is_direct_owner(business, command.user_id)
        now: Microseconds = self._wall_clock.now_unix()
        # Set by every application, so it tells what the stored one did.
        changed: bool = False

        def apply_change(current: BusinessDocument) -> None:
            nonlocal changed
            if owner_by_membership and not is_direct_owner(current, command.user_id):
                raise AccessDeniedError("You are no longer an owner of this business.")

            changed = change(current, member_of(current, command.member_user_id))
            if not changed:
                return

            keep_an_owner(current)
            current.updated_at = now

        business = self._business_repo.update(business.id, apply_change)
        if changed:
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    actor_id=command.user_id,
                    action=action,
                    entity=AuditEntityName("business_member"),
                    entity_id=AuditEntityReference(str(command.member_user_id)),
                    ip_address=command.client_ip_address,
                    created_at=now,
                    updated_at=now,
                )
            )
        return self._business_view_transformer.transform(
            business_view_source(
                business, command.user_id, self._user_repo, self._brand_repo
            )
        )


def member_of(business: BusinessDocument, member_user_id: UserId) -> BusinessMember:
    member: BusinessMember | None = next(
        (member for member in business.members if member.user_id == member_user_id),
        None,
    )
    if member is None:
        raise NotFoundError(f"User {member_user_id} is not a member of the business.")

    return member


def is_direct_owner(business: BusinessDocument, user_id: UserId) -> bool:
    return any(
        member.user_id == user_id and member.role is BusinessMemberRole.OWNER
        for member in business.members
    )


def keep_an_owner(business: BusinessDocument) -> None:
    """Refuses a team without an owner (nothing is stored then)."""

    if not any(member.role is BusinessMemberRole.OWNER for member in business.members):
        raise ConflictError("A business must keep at least one owner.")
