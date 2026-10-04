"""
The admin sees what the reply guard did for each client in the last 7
days, and GUARD_SPIKE when it held back many replies or many messages
tried prompt injection.
"""

from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.client_health import ClientHealthIssue, ClientHealthStatus
from app.schemas.constants.conversations import MessageAuthor, ReplyGuardVerdict
from app.schemas.constants.reply_safety import InjectionSignal
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.admin import AdminClientsQuery, AdminClientSummary
from app.schemas.dto.reply_safety import ClientGuardActivity
from app.schemas.typings.client_health.constrained_integers import (
    GuardedReplyCount,
    InjectionFlagCount,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.client_health.guard_activity import is_guard_spike
from tests.billing.admin_world import AdminWorld, build_admin_world, days_ago


def georgian_summary(world: AdminWorld) -> AdminClientSummary:
    page = world.testbed.list_clients.run(AdminClientsQuery(user_id=world.admin.id))
    return next(item for item in page.items if item.business_id == world.georgian.id)


def add_replies(
    world: AdminWorld, verdicts: list[ReplyGuardVerdict | None], days: float = 1
) -> None:
    created_at = days_ago(world.testbed, days)
    world.testbed.message_repo.save_many(
        [
            MessageDocument(
                conversation_id=ConversationId(),
                business_id=world.georgian.id,
                direction=MessageDirection.OUTBOUND,
                author=MessageAuthor.ASSISTANT,
                text=MessageText("Here you are."),
                guard_verdict=verdict,
                created_at=created_at,
                updated_at=created_at,
            )
            for verdict in verdicts
        ]
    )


def add_customer_messages(
    world: AdminWorld, flags: list[InjectionSignal | None], days: float = 1
) -> None:
    created_at = days_ago(world.testbed, days)
    world.testbed.message_repo.save_many(
        [
            MessageDocument(
                conversation_id=ConversationId(),
                business_id=world.georgian.id,
                direction=MessageDirection.INBOUND,
                author=MessageAuthor.CUSTOMER,
                text=MessageText("Hello"),
                injection_flag=flag,
                created_at=created_at,
                updated_at=created_at,
            )
            for flag in flags
        ]
    )


def test_the_guards_work_of_the_week_is_counted() -> None:
    world = build_admin_world()
    add_replies(
        world,
        [ReplyGuardVerdict.CLEAN] * 20
        + [ReplyGuardVerdict.REWRITTEN] * 2
        + [ReplyGuardVerdict.HANDED_OFF]
        + [None] * 4,
    )
    add_replies(world, [ReplyGuardVerdict.HANDED_OFF] * 3, days=8)
    add_customer_messages(world, [None] * 5 + [InjectionSignal.ROLE_CHANGE] * 2)

    summary = georgian_summary(world)

    assert summary.guard_activity == ClientGuardActivity(
        checked_replies=GuardedReplyCount(23),
        rewritten_replies=GuardedReplyCount(2),
        handed_off_replies=GuardedReplyCount(1),
        injection_flags=InjectionFlagCount(2),
    )
    assert ClientHealthIssue.GUARD_SPIKE not in summary.health_issues


def test_many_held_back_replies_are_a_guard_spike() -> None:
    world = build_admin_world()
    add_replies(
        world,
        [ReplyGuardVerdict.CLEAN] * 20
        + [ReplyGuardVerdict.REWRITTEN] * 3
        + [ReplyGuardVerdict.HANDED_OFF] * 3,
    )

    summary = georgian_summary(world)

    assert ClientHealthIssue.GUARD_SPIKE in summary.health_issues
    assert summary.health_status is not ClientHealthStatus.HEALTHY


def test_many_injection_attempts_are_a_guard_spike() -> None:
    world = build_admin_world()
    add_customer_messages(world, [InjectionSignal.INSTRUCTION_OVERRIDE] * 10)

    assert ClientHealthIssue.GUARD_SPIKE in georgian_summary(world).health_issues


def guard(
    checked: int, rewritten: int, handed_off: int, flags: int = 0
) -> ClientGuardActivity:
    return ClientGuardActivity(
        checked_replies=GuardedReplyCount(checked),
        rewritten_replies=GuardedReplyCount(rewritten),
        handed_off_replies=GuardedReplyCount(handed_off),
        injection_flags=InjectionFlagCount(flags),
    )


def test_the_spike_needs_both_a_count_and_a_share() -> None:
    assert is_guard_spike(guard(24, 2, 2)) is False  # four is not a pattern
    assert is_guard_spike(guard(30, 3, 2)) is True  # one in six
    assert is_guard_spike(guard(31, 3, 2)) is False  # under one in six
    assert is_guard_spike(guard(0, 0, 0, flags=9)) is False
    assert is_guard_spike(guard(0, 0, 0, flags=10)) is True
