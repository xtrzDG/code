from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.dto.businesses import BusinessView, RemoveMemberCommand
from app.use_cases.businesses.member_mutation_guard import MemberMutationGuard


class RemoveMemberUseCase(UseCaseContract[RemoveMemberCommand, BusinessView]):
    """
    Owner removes a member of the team.

    Owners may remove staff, other owners and themselves, but a business
    always keeps at least one owner. The removal is audited
    (MemberMutationGuard).
    """

    def __init__(self, member_mutations: MemberMutationGuard) -> None:
        self._member_mutations: MemberMutationGuard = member_mutations

    def run(self, input_data: RemoveMemberCommand) -> BusinessView:
        return self._member_mutations.apply(
            input_data, remove_member, AuditAction.DELETE
        )


def remove_member(business: BusinessDocument, member: BusinessMember) -> bool:
    business.members = [
        other for other in business.members if other.user_id != member.user_id
    ]
    return True
