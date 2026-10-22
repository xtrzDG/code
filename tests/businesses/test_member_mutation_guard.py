"""Every change to a team member keeps an owner, even when two race."""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.contracts.session_assurance import StepUpGuardContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.businesses import (
    BusinessView,
    ChangeMemberRoleCommand,
    InviteStaffRequest,
    MemberRoleChange,
    RemoveMemberCommand,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import RawEmailAddressInput
from app.transformers.businesses.business_view_transformer import (
    BusinessViewTransformer,
)
from app.use_cases.businesses.change_member_role_use_case import (
    ChangeMemberRoleUseCase,
)
from app.use_cases.businesses.member_mutation_guard import MemberMutationGuard
from app.use_cases.businesses.remove_member_use_case import RemoveMemberUseCase
from tests.businesses.team_steps import invite
from tests.users.accounts_phones import GEORGIA_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed

TIMEOUT_SECONDS: float = 10


class MeetAfterAccess(StepUpGuardContract):
    """Both owners pass the access checks before either changes the team."""

    def __init__(self) -> None:
        self._both_authorized: threading.Barrier = threading.Barrier(2)

    def require_recent_authentication(self) -> None:
        self._both_authorized.wait(timeout=TIMEOUT_SECONDS)


def two_owners() -> tuple[AccountsTestbed, BusinessDocument, UserId, UserId]:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    co_owner_id: UserId = (
        invite(
            testbed,
            owner.user.id,
            business,
            InviteStaffRequest(
                email=RawEmailAddressInput("partner@example.com"),
                role=BusinessMemberRole.OWNER,
            ),
        )
        .members[1]
        .user_id
    )
    return testbed, business, owner.user.id, co_owner_id


def racing_guard(testbed: AccountsTestbed) -> MemberMutationGuard:
    return MemberMutationGuard(
        authorize_business_access=testbed.authorize_business_access,
        business_repo=testbed.business_repo,
        user_repo=testbed.user_repo,
        brand_repo=testbed.brand_repo,
        audit_log_repo=testbed.audit_log_repo,
        business_view_transformer=BusinessViewTransformer(),
        wall_clock=testbed.clock.build_wall_clock(),
        step_up=MeetAfterAccess(),
    )


type TeamChange = Callable[[], BusinessView]


def outcomes(*attempts: TeamChange) -> list[BusinessView | ApplicationError]:
    def attempt(run: TeamChange) -> BusinessView | ApplicationError:
        try:
            return run()
        except ApplicationError as error:
            return error

    with ThreadPoolExecutor(max_workers=len(attempts)) as pool:
        return list(pool.map(attempt, attempts))


def owners_of(testbed: AccountsTestbed, business: BusinessDocument) -> list[UserId]:
    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    return [
        member.user_id
        for member in stored.members
        if member.role is BusinessMemberRole.OWNER
    ]


def test_two_owners_demoting_each_other_at_once_leave_one_owner() -> None:
    testbed, business, owner_id, co_owner_id = two_owners()
    change_role = ChangeMemberRoleUseCase(member_mutations=racing_guard(testbed))
    entries_before = len(testbed.audit_log_repo.list_by_business(business.id))

    def demote(actor_id: UserId, member_id: UserId) -> TeamChange:
        return lambda: change_role.run(
            ChangeMemberRoleCommand(
                user_id=actor_id,
                business_id=business.id,
                member_user_id=member_id,
                change=MemberRoleChange(role=BusinessMemberRole.STAFF),
            )
        )

    results = outcomes(demote(owner_id, co_owner_id), demote(co_owner_id, owner_id))

    assert sum(isinstance(result, BusinessView) for result in results) == 1
    assert sum(isinstance(result, ConflictError) for result in results) == 1
    assert len(owners_of(testbed, business)) == 1
    entries = testbed.audit_log_repo.list_by_business(business.id)
    assert [entry.action for entry in entries[entries_before:]] == [AuditAction.UPDATE]


def test_two_owners_removing_each_other_at_once_leave_one_owner() -> None:
    testbed, business, owner_id, co_owner_id = two_owners()
    remove_member = RemoveMemberUseCase(member_mutations=racing_guard(testbed))

    def remove(actor_id: UserId, member_id: UserId) -> TeamChange:
        return lambda: remove_member.run(
            RemoveMemberCommand(
                user_id=actor_id,
                business_id=business.id,
                member_user_id=member_id,
            )
        )

    results = outcomes(remove(owner_id, co_owner_id), remove(co_owner_id, owner_id))

    assert sum(isinstance(result, BusinessView) for result in results) == 1
    assert sum(isinstance(result, ConflictError) for result in results) == 1
    assert len(owners_of(testbed, business)) == 1


def test_a_member_who_left_cannot_be_changed() -> None:
    testbed, business, owner_id, co_owner_id = two_owners()
    testbed.remove_member.run(
        RemoveMemberCommand(
            user_id=owner_id, business_id=business.id, member_user_id=co_owner_id
        )
    )

    with pytest.raises(ApplicationError, match="is not a member"):
        testbed.change_member_role.run(
            ChangeMemberRoleCommand(
                user_id=owner_id,
                business_id=business.id,
                member_user_id=co_owner_id,
                change=MemberRoleChange(role=BusinessMemberRole.STAFF),
            )
        )
