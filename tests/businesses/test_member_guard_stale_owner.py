"""An owner removed or demoted while their own team change waits changes nothing."""

import threading
from collections.abc import Callable

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
from app.schemas.exceptions.application_errors import AccessDeniedError
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


class HeldAfterAccess(StepUpGuardContract):
    """The stale owner's request: authorized, then held until `release`."""

    def __init__(self) -> None:
        self.authorized: threading.Event = threading.Event()
        self.release: threading.Event = threading.Event()

    def require_recent_authentication(self) -> None:
        self.authorized.set()
        assert self.release.wait(timeout=TIMEOUT_SECONDS)


class Passes(StepUpGuardContract):
    def require_recent_authentication(self) -> None:
        return None


def three_owners() -> tuple[AccountsTestbed, BusinessDocument, list[UserId]]:
    testbed = build_accounts_testbed()
    first = testbed.sign_in_with_phone(GEORGIA_MOBILE).user.id
    business = testbed.create_restaurant(first)
    view: BusinessView | None = None
    for email in ("second@example.com", "third@example.com"):
        view = invite(
            testbed,
            first,
            business,
            InviteStaffRequest(
                email=RawEmailAddressInput(email), role=BusinessMemberRole.OWNER
            ),
        )
    assert view is not None
    return testbed, business, [member.user_id for member in view.members]


def guard(
    testbed: AccountsTestbed, step_up: StepUpGuardContract
) -> MemberMutationGuard:
    return MemberMutationGuard(
        authorize_business_access=testbed.authorize_business_access,
        business_repo=testbed.business_repo,
        user_repo=testbed.user_repo,
        brand_repo=testbed.brand_repo,
        audit_log_repo=testbed.audit_log_repo,
        business_view_transformer=BusinessViewTransformer(),
        wall_clock=testbed.clock.build_wall_clock(),
        step_up=step_up,
    )


def run_held(
    held: HeldAfterAccess,
    stale_change: Callable[[], BusinessView],
    meanwhile: Callable[[], BusinessView],
) -> BaseException | None:
    """The stale change passes access, `meanwhile` is stored, then it lands."""

    outcome: list[BaseException | None] = []

    def attempt() -> None:
        try:
            stale_change()
            outcome.append(None)
        except AccessDeniedError as error:
            outcome.append(error)

    thread = threading.Thread(target=attempt)
    thread.start()
    assert held.authorized.wait(timeout=TIMEOUT_SECONDS)
    meanwhile()
    held.release.set()
    thread.join(timeout=TIMEOUT_SECONDS)
    assert not thread.is_alive()
    return outcome[0]


def members_of(
    testbed: AccountsTestbed, business: BusinessDocument
) -> dict[UserId, BusinessMemberRole]:
    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    return {member.user_id: member.role for member in stored.members}


def test_an_owner_removed_meanwhile_cannot_remove_another_owner() -> None:
    testbed, business, (first, second, third) = three_owners()
    held = HeldAfterAccess()
    entries_before = len(testbed.audit_log_repo.list_by_business(business.id))

    def remove(
        actor: UserId, member: UserId, step_up: StepUpGuardContract
    ) -> Callable[[], BusinessView]:
        return lambda: RemoveMemberUseCase(
            member_mutations=guard(testbed, step_up)
        ).run(
            RemoveMemberCommand(
                user_id=actor, business_id=business.id, member_user_id=member
            )
        )

    outcome = run_held(
        held, remove(second, third, held), remove(first, second, Passes())
    )

    assert isinstance(outcome, AccessDeniedError)
    assert set(members_of(testbed, business)) == {first, third}
    entries = testbed.audit_log_repo.list_by_business(business.id)[entries_before:]
    assert [entry.actor_id for entry in entries] == [first]


def test_an_owner_demoted_meanwhile_cannot_change_a_role() -> None:
    new_role = BusinessMemberRole.STAFF
    testbed, business, (first, second, third) = three_owners()
    held = HeldAfterAccess()

    def demote(
        actor: UserId, member: UserId, step_up: StepUpGuardContract
    ) -> Callable[[], BusinessView]:
        return lambda: ChangeMemberRoleUseCase(
            member_mutations=guard(testbed, step_up)
        ).run(
            ChangeMemberRoleCommand(
                user_id=actor,
                business_id=business.id,
                member_user_id=member,
                change=MemberRoleChange(role=new_role),
            )
        )

    outcome = run_held(
        held, demote(second, third, held), demote(first, second, Passes())
    )

    assert isinstance(outcome, AccessDeniedError)
    assert members_of(testbed, business) == {
        first: BusinessMemberRole.OWNER,
        second: new_role,
        third: BusinessMemberRole.OWNER,
    }


def test_an_owner_may_still_step_down_while_another_owner_stays() -> None:
    testbed, business, (first, second, _third) = three_owners()

    view = ChangeMemberRoleUseCase(member_mutations=guard(testbed, Passes())).run(
        ChangeMemberRoleCommand(
            user_id=second,
            business_id=business.id,
            member_user_id=second,
            change=MemberRoleChange(role=BusinessMemberRole.STAFF),
        )
    )

    assert members_of(testbed, business)[second] is BusinessMemberRole.STAFF
    assert members_of(testbed, business)[first] is BusinessMemberRole.OWNER
    assert view.id == business.id
    assert AuditAction.UPDATE in [
        entry.action for entry in testbed.audit_log_repo.list_by_business(business.id)
    ]
