"""
How each record of a client becomes lines of its story: audit entries,
invoices, used credit, product steps, health changes, the done-for-you
request. Pure mappings; the use case reads the records.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.analytics import ProductEventName
from app.schemas.constants.billing import BillingCreditKind, InvoiceStatus
from app.schemas.constants.client_health import ClientTimelineEvent as Event
from app.schemas.constants.client_health import ClientTimelineKind as Kind
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.billing import InvoiceDocument, OnboardingRequestDocument
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.domain.client_health_changes import ClientHealthChangeDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.client_story import ClientTimelineEntry
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor

# Reading a record is no story; signing in is a person's, not a client's.
QUIET_AUDIT_ACTIONS: frozenset[AuditAction] = frozenset(
    {AuditAction.VIEW, AuditAction.LOGIN}
)
SUPPORT_AUDIT_ACTIONS: frozenset[AuditAction] = frozenset(
    {
        AuditAction.ADMIN_ACCESS,
        AuditAction.SUPPORT_ACCESS_START,
        AuditAction.SUPPORT_ACCESS_END,
    }
)
ADMIN_AUDIT_ACTIONS: frozenset[AuditAction] = frozenset(
    action for action in AuditAction if action.value.startswith("admin_")
) - {AuditAction.ADMIN_ACCESS}
PRODUCT_LINES: dict[ProductEventName, tuple[Kind, Event]] = {
    ProductEventName.BUSINESS_CREATED: (Kind.MILESTONE, Event.BUSINESS_CREATED),
    ProductEventName.LAUNCH_SUCCEEDED: (Kind.MILESTONE, Event.LAUNCH_SUCCEEDED),
    ProductEventName.LAUNCH_BLOCKED: (Kind.MILESTONE, Event.LAUNCH_BLOCKED),
    ProductEventName.DPA_ACCEPTED: (Kind.MILESTONE, Event.DPA_ACCEPTED),
    ProductEventName.CHANNEL_CONNECTED: (Kind.MILESTONE, Event.CHANNEL_CONNECTED),
    ProductEventName.TEST_CHAT_TRIED: (Kind.MILESTONE, Event.TEST_CHAT_TRIED),
    ProductEventName.WENT_LIVE: (Kind.MILESTONE, Event.WENT_LIVE),
    ProductEventName.FIRST_REAL_CONVERSATION: (
        Kind.MILESTONE,
        Event.FIRST_REAL_CONVERSATION,
    ),
    ProductEventName.FIRST_BOOKING: (Kind.MILESTONE, Event.FIRST_BOOKING),
    ProductEventName.FIRST_HANDOFF: (Kind.MILESTONE, Event.FIRST_HANDOFF),
    ProductEventName.TRIAL_STARTED: (Kind.BILLING, Event.TRIAL_STARTED),
    ProductEventName.SUBSCRIBED: (Kind.BILLING, Event.SUBSCRIBED),
    ProductEventName.PLAN_CHANGED: (Kind.BILLING, Event.PLAN_CHANGED),
    ProductEventName.CANCELLED: (Kind.BILLING, Event.CANCELLED),
}


def audit_lines(
    entries: Sequence[AuditLogEntryDocument],
    credits: Sequence[BillingCreditDocument],
) -> list[ClientTimelineEntry]:
    """
    Every entry but views and sign-ins; an admin's grant of credit names
    its amount (from the ledger line the entry points at).
    """

    granted: dict[str, BillingCreditDocument] = {
        str(line.id): line for line in credits if line.kind is BillingCreditKind.GRANTED
    }
    lines: list[ClientTimelineEntry] = []
    for entry in entries:
        if entry.action in QUIET_AUDIT_ACTIONS:
            continue

        credit = granted.get(str(entry.entity_id)) if entry.entity_id else None
        lines.append(
            ClientTimelineEntry(
                kind=(
                    Kind.ADMIN_ACTION
                    if entry.action in ADMIN_AUDIT_ACTIONS
                    else Kind.SUPPORT
                    if entry.action in SUPPORT_AUDIT_ACTIONS
                    else Kind.CHANGE
                ),
                event=Event.AUDIT_ENTRY,
                occurred_at=entry.created_at,
                actor_user_id=entry.actor_id,
                audit_action=entry.action,
                audit_entity=entry.entity,
                reason=entry.reason,
                amount=None if credit is None else credit_money(credit),
            )
        )

    return lines


def invoice_lines(invoices: Sequence[InvoiceDocument]) -> list[ClientTimelineEntry]:
    """An invoice issued, paid (how, when recorded by hand) or failed."""

    lines: list[ClientTimelineEntry] = []
    for invoice in invoices:
        if invoice.status is InvoiceStatus.VOID:
            continue

        lines.append(invoice_line(invoice, Event.INVOICE_ISSUED, invoice.created_at))
        if invoice.status is InvoiceStatus.PAID and invoice.paid_at is not None:
            lines.append(invoice_line(invoice, Event.INVOICE_PAID, invoice.paid_at))
        elif invoice.status is InvoiceStatus.FAILED:
            failed_at: Microseconds = invoice.updated_at
            lines.append(invoice_line(invoice, Event.INVOICE_FAILED, failed_at))

    return lines


def invoice_line(
    invoice: InvoiceDocument, event: Event, occurred_at: Microseconds
) -> ClientTimelineEntry:
    manual = invoice.manual_payment if event is Event.INVOICE_PAID else None
    return ClientTimelineEntry(
        kind=Kind.BILLING,
        event=event,
        occurred_at=occurred_at,
        actor_user_id=None if manual is None else manual.recorded_by,
        amount=Money(
            amount_minor=invoice.amount_minor, currency_code=invoice.currency_code
        ),
        invoice_number=invoice.number,
        payment_method=None if manual is None else manual.method,
        discount_percent=(
            invoice.discount_percent if event is Event.INVOICE_ISSUED else None
        ),
    )


def credit_lines(credits: Sequence[BillingCreditDocument]) -> list[ClientTimelineEntry]:
    """Credit an invoice used (a grant is told by its audit entry)."""

    return [
        ClientTimelineEntry(
            kind=Kind.BILLING,
            event=Event.CREDIT_USED,
            occurred_at=line.created_at,
            amount=credit_money(line),
        )
        for line in credits
        if line.kind is BillingCreditKind.USED
    ]


def product_lines(events: Sequence[ProductEventDocument]) -> list[ClientTimelineEntry]:
    """The setup's milestones and the subscription's steps."""

    lines: list[ClientTimelineEntry] = []
    for event in events:
        known = PRODUCT_LINES.get(event.name)
        if known is None:
            continue

        properties = event.properties
        amount: Money | None = None
        if properties.monthly_amount is not None and properties.currency_code:
            amount = Money(
                amount_minor=MoneyAmountMinor(int(properties.monthly_amount)),
                currency_code=properties.currency_code,
            )

        lines.append(
            ClientTimelineEntry(
                kind=known[0],
                event=known[1],
                occurred_at=event.occurred_at,
                actor_user_id=event.user_id,
                amount=amount,
                plan_key=properties.plan_key,
                previous_plan_key=properties.previous_plan_key,
                channel=properties.channel,
            )
        )

    return lines


def health_lines(
    changes: Sequence[ClientHealthChangeDocument],
) -> list[ClientTimelineEntry]:
    return [
        ClientTimelineEntry(
            kind=Kind.HEALTH,
            event=Event.HEALTH_CHANGED,
            occurred_at=change.changed_at,
            health_from=change.previous_status,
            health_to=change.status,
            health_issues=list(change.issues),
        )
        for change in changes
    ]


def onboarding_lines(
    request: OnboardingRequestDocument | None,
) -> list[ClientTimelineEntry]:
    if request is None:
        return []

    return [
        ClientTimelineEntry(
            kind=Kind.ONBOARDING,
            event=Event.ONBOARDING_REQUESTED,
            occurred_at=request.requested_at,
            actor_user_id=request.requested_by,
            plan_key=request.plan_key,
        )
    ]


def credit_money(line: BillingCreditDocument) -> Money:
    return Money(
        amount_minor=MoneyAmountMinor(int(line.amount_minor)),
        currency_code=line.currency_code,
    )
