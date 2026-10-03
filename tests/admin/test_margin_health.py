"""
A free trial costs the platform by design: the admin flags a negative
margin only for a client that pays (now that dollar costs convert into
every subscription currency, every trial would otherwise look critical).
"""

from app.schemas.constants.billing import SubscriptionStatus, UsageKind
from app.schemas.constants.client_health import ClientHealthIssue, ClientHealthStatus
from app.schemas.dto.admin import AdminClientsQuery, AdminClientSummary
from tests.billing.admin_world import AdminWorld, build_admin_world


def georgian_summary(world: AdminWorld) -> AdminClientSummary:
    page = world.testbed.list_clients.run(AdminClientsQuery(user_id=world.admin.id))
    return next(item for item in page.items if item.business_id == world.georgian.id)


def spend_on_calls(world: AdminWorld) -> None:
    world.testbed.record_usage(
        world.georgian.id, UsageKind.VOICE_SECONDS, 60_000, 80_000_000
    )
    world.testbed.clock.advance(hours=1)


def test_a_trial_that_costs_money_is_not_a_negative_margin() -> None:
    world = build_admin_world()
    spend_on_calls(world)

    summary = georgian_summary(world)

    assert summary.cost.margin is not None
    assert int(summary.cost.margin.amount_minor) < 0
    assert ClientHealthIssue.NEGATIVE_MARGIN not in summary.health_issues


def test_a_paying_client_that_costs_more_than_it_pays_is_critical() -> None:
    world = build_admin_world()
    spend_on_calls(world)
    subscription = world.testbed.subscription(world.georgian.id)
    subscription.status = SubscriptionStatus.ACTIVE
    world.testbed.subscription_repo.save(subscription)

    summary = georgian_summary(world)

    assert summary.health_issues[0] is ClientHealthIssue.NEGATIVE_MARGIN
    assert summary.health_status is ClientHealthStatus.CRITICAL
