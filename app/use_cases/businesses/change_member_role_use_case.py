from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.dto.businesses import BusinessView, ChangeMemberRoleCommand
from app.use_cases.businesses.member_mutation_guard import (
    MemberMutationGuard,
    member_of,
)
from app.use_cases.businesses.owner_promotion_sweep import OwnerPromotionSweep


class ChangeMemberRoleUseCase(UseCaseContract[ChangeMemberRoleCommand, BusinessView]):
    """
    Owner makes a team member an owner or staff (themselves included).

    A business always keeps at least one owner, so the last owner cannot
    be made staff. Asking for the role a member already has changes
    nothing; a real change is audited (MemberMutationGuard). A member made
    an owner signs in again (OwnerPromotionSweep): every session of theirs
    ends before the change is stored, so a sweep that fails stores nothing
    and a retry sweeps again, and once more after it is stored (a session
    opened in between). A promotion refused while it is stored (the actor
    lost ownership meanwhile) may still have signed the member out.
    """

    def __init__(
        self,
        member_mutations: MemberMutationGuard,
        owner_promotions: OwnerPromotionSweep,
    ) -> None:
        self._member_mutations: MemberMutationGuard = member_mutations
        self._owner_promotions: OwnerPromotionSweep = owner_promotions

    def run(self, input_data: ChangeMemberRoleCommand) -> BusinessView:
        new_role: BusinessMemberRole = input_data.change.role
        # Set by every application of the change: what the stored one did.
        is_promotion: bool = False

        def sweep_before_promotion(business: BusinessDocument) -> None:
            member: BusinessMember = member_of(business, input_data.member_user_id)
            if new_role is BusinessMemberRole.OWNER and member.role is not new_role:
                self._end_sessions(input_data)

        def change_role(business: BusinessDocument, member: BusinessMember) -> bool:
            nonlocal is_promotion
            is_promotion = False
            if member.role is new_role:
                return False

            is_promotion = new_role is BusinessMemberRole.OWNER
            business.members = [
                other.model_copy(update={"role": new_role})
                if other.user_id == member.user_id
                else other
                for other in business.members
            ]
            return True

        view: BusinessView = self._member_mutations.apply(
            input_data, change_role, AuditAction.UPDATE, sweep_before_promotion
        )
        if is_promotion:
            # A session opened between the first sweep and the stored change.
            self._end_sessions(input_data)
        return view

    def _end_sessions(self, input_data: ChangeMemberRoleCommand) -> None:
        self._owner_promotions.end_sessions_of(
            input_data.member_user_id,
            input_data.user_id,
            input_data.client_ip_address,
        )
