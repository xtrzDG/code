from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
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
    RemoveMemberCommand,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)


class RemoveMemberUseCase(UseCaseContract[RemoveMemberCommand, BusinessView]):
    """
    Owner removes a member of the team.

    Owners may remove staff, other owners and themselves, but a business
    always keeps at least one owner. The removal is audited.
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

    def run(self, input_data: RemoveMemberCommand) -> BusinessView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()

        def remove_member(current: BusinessDocument) -> None:
            # Checked and removed on the business as stored now, so a change
            # saved meanwhile (settings, another member) is kept.
            removed_member: BusinessMember | None = next(
                (
                    member
                    for member in current.members
                    if member.user_id == input_data.member_user_id
                ),
                None,
            )
            if removed_member is None:
                raise NotFoundError(
                    f"User {input_data.member_user_id} is not a member of the business."
                )

            owner_count: int = sum(
                1
                for member in current.members
                if member.role is BusinessMemberRole.OWNER
            )
            if removed_member.role is BusinessMemberRole.OWNER and owner_count == 1:
                raise ConflictError("A business must keep at least one owner.")

            current.members = [
                member
                for member in current.members
                if member.user_id != input_data.member_user_id
            ]
            current.updated_at = now

        business = self._business_repo.update(business.id, remove_member)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.DELETE,
                entity=AuditEntityName("business_member"),
                entity_id=AuditEntityReference(str(input_data.member_user_id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
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
