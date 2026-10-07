"""
A client's story on the admin page: the audit log (views left out, the
admins' reasons kept), invoices, credit, the subscription's steps, health
changes, milestones and the done-for-you request, newest first, page by
page without a line lost or shown twice.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.analytics import ProductEventName, ProductEventSource
from app.schemas.constants.billing import InvoiceKind
from app.schemas.constants.client_health import (
    ClientHealthIssue,
    ClientHealthStatus,
    ClientTimelineEvent,
    ClientTimelineKind,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.client_health_changes import ClientHealthChangeDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.dto.client_story import ClientTimelineEntry, ClientTimelineQuery
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.analytics.prefixed_id import ProductEventId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.users.prefixed_id import UserId
from tests.admin_actions.action_steps import credit, mark_paid
from tests.admin_actions.action_world import REASON, ActionWorld
from tests.billing.grace_steps import end_trial

Event = ClientTimelineEvent


def tell(world: ActionWorld) -> None:
    """Two weeks of a client: live, a look, credit, trial end, paid by hand."""

    clock = world.testbed.clock
    world.product_event_repo.record(
        ProductEventDocument(
            id=ProductEventId(),
            name=ProductEventName.WENT_LIVE,
            occurred_at=clock.now(),
            source=ProductEventSource.SERVER,
            user_id=world.owner.id,
            business_id=world.business.id,
        )
    )
    clock.advance(hours=2)
    world.testbed.audit_log_repo.append(
        AuditLogEntryDocument(
            business_id=world.business.id,
            actor_id=world.owner.id,
            action=AuditAction.VIEW,
            entity=AuditEntityName("conversation"),
            created_at=clock.now(),
        )
    )
    clock.advance(days=1)
    credit(world, world.accountant)
    clock.advance(days=13, hours=1)
    end_trial(world.testbed)
    clock.advance(hours=1)
    world.health_repo.add(
        ClientHealthChangeDocument(
            business_id=world.business.id,
            previous_status=ClientHealthStatus.ATTENTION,
            status=ClientHealthStatus.CRITICAL,
            issues=[ClientHealthIssue.PAYMENT_PAST_DUE],
            changed_at=clock.now(),
        )
    )
    clock.advance(days=1)
    period = next(
        invoice
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
    )
    mark_paid(world, world.founder, period.id)


def page(
    world: ActionWorld, size: int, cursor: object = None
) -> tuple[list[ClientTimelineEntry], object]:
    result = world.timeline.run(
        ClientTimelineQuery(
            user_id=world.support.id,
            business_id=world.business.id,
            page=PageRequest(size=PageSize(size), cursor=cursor),  # type: ignore[arg-type]
        )
    )
    return result.items, result.next_cursor


def test_the_story_reads_newest_first_with_people_and_reasons() -> None:
    world = ActionWorld()
    tell(world)

    lines, cursor = page(world, 50)

    assert cursor is None
    assert [line.occurred_at for line in lines] == sorted(
        (line.occurred_at for line in lines), key=int, reverse=True
    )
    events = [(line.kind, line.event, line.audit_action) for line in lines]
    assert events[:3] == [
        (
            ClientTimelineKind.ADMIN_ACTION,
            Event.AUDIT_ENTRY,
            AuditAction.ADMIN_INVOICE_MARKED_PAID,
        ),
        (ClientTimelineKind.BILLING, Event.INVOICE_PAID, None),
        (ClientTimelineKind.HEALTH, Event.HEALTH_CHANGED, None),
    ]
    assert events[-1] == (ClientTimelineKind.MILESTONE, Event.WENT_LIVE, None)
    assert all(line.audit_action is not AuditAction.VIEW for line in lines)
    paid_by_hand = lines[0]
    assert (paid_by_hand.actor_name, paid_by_hand.reason) == ("Nino", REASON)
    grant = next(
        line for line in lines if line.audit_action is AuditAction.ADMIN_CREDIT_GRANTED
    )
    assert grant.amount is not None and int(grant.amount.amount_minor) == 10_000
    assert str(grant.actor_name) == "Levan"
    assert any(line.event is Event.CREDIT_USED for line in lines)
    assert lines[2].health_to is ClientHealthStatus.CRITICAL


def test_pages_cover_the_story_once_in_order() -> None:
    world = ActionWorld()
    tell(world)
    whole, _ = page(world, 50)

    seen: list[ClientTimelineEntry] = []
    cursor: object = None
    for _ in range(20):
        lines, cursor = page(world, 2, cursor)
        seen.extend(lines)
        if cursor is None:
            break

    assert cursor is None
    assert [(line.occurred_at, line.event) for line in seen] == [
        (line.occurred_at, line.event) for line in whole
    ]


def test_a_full_page_of_the_audit_log_holds_back_older_lines_of_other_sources() -> None:
    world = ActionWorld()
    clock = world.testbed.clock
    world.health_repo.add(
        ClientHealthChangeDocument(
            business_id=world.business.id,
            previous_status=ClientHealthStatus.HEALTHY,
            status=ClientHealthStatus.ATTENTION,
            changed_at=Microseconds(int(clock.now()) - 1),
        )
    )
    for _ in range(3):
        clock.advance(hours=1)
        credit(world, world.founder)

    first, cursor = page(world, 2)
    rest, end = page(world, 2, cursor)

    assert [line.event for line in first] == [Event.AUDIT_ENTRY] * 2
    assert [line.event for line in rest] == [Event.AUDIT_ENTRY, Event.HEALTH_CHANGED]
    assert end is None
    assert UserId(str(world.founder.id)) == first[0].actor_user_id
