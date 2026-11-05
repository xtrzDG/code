"""
A client's story on the admin client page (R13): the platform team's notes
(pinned first) and the timeline that merges the audit log, billing, health
changes, the setup's milestones and the done-for-you request.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.analytics import TunnelStepKey
from app.schemas.constants.billing import ManualPaymentMethod, PlanKey
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.client_health import (
    ClientHealthIssue,
    ClientHealthStatus,
    ClientTimelineEvent,
    ClientTimelineKind,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.dto.billing import Money
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.access.constrained_strings import AdminActionReason
from app.schemas.typings.billing.constrained_integers import ClientDiscountPercent
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.client_health.booleans import IsClientNotePinned
from app.schemas.typings.client_health.constrained_strings import ClientNoteText
from app.schemas.typings.client_health.prefixed_id import ClientNoteId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.invoicing.constrained_strings import InvoiceNumber
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import UserDisplayName


class ClientNoteBody(ImmutableDTO):
    """POST /v1/admin/clients/{business_id}/notes: a new note."""

    text: ClientNoteText
    is_pinned: IsClientNotePinned = False


class ClientNoteChange(ImmutableDTO):
    """PATCH …/notes/{note_id}: new words, pinned or not (what is sent)."""

    text: ClientNoteText | None = None
    is_pinned: IsClientNotePinned | None = None


class CreateClientNoteCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    body: ClientNoteBody


class UpdateClientNoteCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    note_id: ClientNoteId
    body: ClientNoteChange


class DeleteClientNoteCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    note_id: ClientNoteId


class ClientNoteView(ImmutableDTO):
    """A note with its author's name (None for someone without one)."""

    id: ClientNoteId
    text: ClientNoteText
    is_pinned: IsClientNotePinned
    author_user_id: UserId
    author_name: UserDisplayName | None = None
    created_at: Microseconds
    updated_at: Microseconds


class ClientNoteList(ImmutableDTO):
    """The client's notes: pinned first, then the newest first."""

    items: list[ClientNoteView] = Field(default_factory=list[ClientNoteView])


class ClientTimelineQuery(ImmutableDTO):
    """One page of a client's story, newest first."""

    user_id: UserId
    business_id: BusinessId
    page: PageRequest = PageRequest()


class ClientTimelineEntry(ImmutableDTO):
    """
    One line of a client's story: what (`kind`, `event`), when, who (the
    audit log's person) and the facts its event has. AUDIT_ENTRY names the
    audit action and entity; admin actions carry the admin's reason;
    billing lines the amount, plan, invoice number or payment method;
    health changes the statuses and issues; milestones the channel or the
    tunnel screen.
    """

    kind: ClientTimelineKind
    event: ClientTimelineEvent
    occurred_at: Microseconds
    actor_user_id: UserId | None = None
    actor_name: UserDisplayName | None = None
    audit_action: AuditAction | None = None
    audit_entity: AuditEntityName | None = None
    reason: AdminActionReason | None = None
    amount: Money | None = None
    plan_key: PlanKey | None = None
    previous_plan_key: PlanKey | None = None
    invoice_number: InvoiceNumber | None = None
    payment_method: ManualPaymentMethod | None = None
    discount_percent: ClientDiscountPercent | None = None
    health_from: ClientHealthStatus | None = None
    health_to: ClientHealthStatus | None = None
    health_issues: list[ClientHealthIssue] = Field(
        default_factory=list[ClientHealthIssue]
    )
    channel: ChannelKind | None = None
    tunnel_step: TunnelStepKey | None = None


class ClientTimelinePage(ImmutableDTO):
    """One page of the story; `next_cursor` is None at its beginning."""

    items: list[ClientTimelineEntry]
    next_cursor: PageCursor | None = None
