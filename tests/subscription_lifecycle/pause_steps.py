"""Steps of the pause tests: pause, resume, move time to the pause's edges."""

from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import BillingOverview
from app.schemas.dto.subscription_lifecycle import (
    PauseSubscriptionCommand,
    PauseSubscriptionRequest,
    ResumeSubscriptionCommand,
)
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    PauseMonthCount,
)
from tests.subscription_lifecycle.lifecycle_world import LifecycleWorld

HOUR_MICROSECONDS: int = 60 * 60 * 1_000_000


def pause(
    world: LifecycleWorld, owner: UserDocument, business: BusinessDocument, months: int
) -> BillingOverview:
    return world.pause.run(
        PauseSubscriptionCommand(
            user_id=owner.id,
            business_id=business.id,
            request=PauseSubscriptionRequest(months=PauseMonthCount(months)),
        )
    )


def resume(
    world: LifecycleWorld, owner: UserDocument, business: BusinessDocument
) -> BillingOverview:
    return world.resume.run(
        ResumeSubscriptionCommand(user_id=owner.id, business_id=business.id)
    )


def reach_pause_start(world: LifecycleWorld, business: BusinessDocument) -> None:
    """An hour past the end of the paid period, then the pause job runs."""

    starts_at = world.current(business).pause_starts_at
    assert starts_at is not None
    world.clock.move_to(type(starts_at)(int(starts_at) + HOUR_MICROSECONDS))
    world.run_pause_job()


def reach_period_end(world: LifecycleWorld, business: BusinessDocument) -> None:
    period_end = world.current(business).period_end
    world.clock.move_to(type(period_end)(int(period_end) + HOUR_MICROSECONDS))


def pause_invoices(
    world: LifecycleWorld, business: BusinessDocument
) -> list[InvoiceDocument]:
    """The business's invoices worded as a seasonal pause (English line)."""

    return [
        invoice
        for invoice in world.invoices(business.id)
        if any("seasonal pause" in str(line.text) for line in invoice.line_texts)
    ]
