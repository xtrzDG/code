from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import (
    AuditLogRepoContract,
    BusinessRepoContract,
    UserRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.businesses import (
    BusinessView,
    BusinessViewSource,
    ChangeMemberRoleCommand,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)


class ChangeMemberRoleUseCase(UseCaseContract[ChangeMemberRoleCommand, BusinessView]):
    """
    Owner makes a team member an owner or staff (themselves included).

    A business always keeps at least one owner, so the last owner cannot
    be made staff. Asking for the role a member already has changes
    nothing; a real change is audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        audit_log_repo: AuditLogRepoContract,
        business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._business_repo: BusinessRepoContract = business_repo
        self._user_repo: UserRepoContract = user_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ] = business_view_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ChangeMemberRoleCommand) -> BusinessView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        member: BusinessMember | None = next(
            (
                member
                for member in business.members
                if member.user_id == input_data.member_user_id
            ),
            None,
        )
        if member is None:
            raise NotFoundError(
                f"User {input_data.member_user_id} is not a member of the business."
            )

        new_role: BusinessMemberRole = input_data.change.role
        if member.role is new_role:
            return self._view(business, input_data)

        owner_count: int = sum(
            1 for other in business.members if other.role is BusinessMemberRole.OWNER
        )
        if member.role is BusinessMemberRole.OWNER and owner_count == 1:
            raise ConflictError("A business must keep at least one owner.")

        now: Microseconds = self._wall_clock.now_unix()
        business.members = [
            BusinessMember(user_id=other.user_id, role=new_role)
            if other.user_id == member.user_id
            else other
            for other in business.members
        ]
        business.updated_at = now
        self._business_repo.save(business)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=AuditEntityName("business_member"),
                entity_id=AuditEntityReference(str(member.user_id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return self._view(business, input_data)

    def _view(
        self,
        business: BusinessDocument,
        input_data: ChangeMemberRoleCommand,
    ) -> BusinessView:
        member_users: list[UserDocument] = [
            user
            for member in business.members
            if (user := self._user_repo.get(member.user_id)) is not None
        ]
        return self._business_view_transformer.transform(
            BusinessViewSource(
                business=business,
                member_users=member_users,
                viewer_id=input_data.user_id,
            )
        )
