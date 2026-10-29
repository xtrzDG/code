from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.dto.businesses import BusinessView, ChangeMemberRoleCommand
from app.use_cases.businesses.member_mutation_guard import MemberMutationGuard


class ChangeMemberRoleUseCase(UseCaseContract[ChangeMemberRoleCommand, BusinessView]):
    """
    Owner makes a team member an owner or staff (themselves included).

    A business always keeps at least one owner, so the last owner cannot
    be made staff. Asking for the role a member already has changes
    nothing; a real change is audited (MemberMutationGuard).
    """

    def __init__(self, member_mutations: MemberMutationGuard) -> None:
        self._member_mutations: MemberMutationGuard = member_mutations

    def run(self, input_data: ChangeMemberRoleCommand) -> BusinessView:
        new_role: BusinessMemberRole = input_data.change.role

        def change_role(business: BusinessDocument, member: BusinessMember) -> bool:
            if member.role is new_role:
                return False

            business.members = [
                other.model_copy(update={"role": new_role})
                if other.user_id == member.user_id
                else other
                for other in business.members
            ]
            return True

        return self._member_mutations.apply(input_data, change_role, AuditAction.UPDATE)
