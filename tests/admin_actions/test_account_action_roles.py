"""
Who may act on a client's account: SUPER and BILLING admins; a support
admin (read-only) is refused, and nothing of the client changes.
"""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.exceptions.application_errors import AccessDeniedError
from tests.admin_actions.action_steps import (
    Act,
    credit,
    discount,
    extend,
    mark_paid,
    override,
    waive,
)
from tests.admin_actions.action_world import REASON, ActionWorld

ACTIONS: list[Act] = [extend, discount, credit, waive, mark_paid, override]


@pytest.mark.parametrize("act", ACTIONS, ids=lambda act: act.__name__)
def test_a_support_admin_is_refused_and_nothing_changes(act: Act) -> None:
    world = ActionWorld()
    before = world.testbed.subscription(world.business.id)

    with pytest.raises(AccessDeniedError):
        act(world, world.support)

    assert world.testbed.subscription(world.business.id) == before
    assert world.testbed.billing_credit_repo.list_by_business(world.business.id) == []
    assert world.testbed.audit_log_repo.list_by_business(world.business.id) == []


@pytest.mark.parametrize(
    ("act", "action"),
    [
        (extend, AuditAction.ADMIN_TRIAL_EXTENDED),
        (discount, AuditAction.ADMIN_DISCOUNT_GIVEN),
        (credit, AuditAction.ADMIN_CREDIT_GRANTED),
        (waive, AuditAction.ADMIN_SETUP_FEE_WAIVED),
        (override, AuditAction.ADMIN_PLAN_OVERRIDDEN),
    ],
    ids=lambda value: getattr(value, "__name__", str(value)),
)
def test_a_billing_admin_acts_and_the_audit_log_keeps_the_reason(
    act: Act, action: AuditAction
) -> None:
    world = ActionWorld()

    receipt = act(world, world.accountant)

    [entry] = world.testbed.audit_log_repo.list_by_business(world.business.id)
    assert receipt.action is action
    assert receipt.audit_log_entry_id == entry.id
    assert (entry.action, entry.actor_id, entry.reason) == (
        action,
        world.accountant.id,
        REASON,
    )
