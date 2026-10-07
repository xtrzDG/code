"""
What the segment use cases share: owner access, loading a segment, its
view, its rules from a request, the audit entries and member pages.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.repositories.customer_repositories import (
    CustomerSegmentRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.customer_segments import CustomerSegmentDocument, SegmentRules
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.contacts import ContactActivityTotals, ContactSummaryView
from app.schemas.dto.customers.customer_segments import SegmentRulesBody, SegmentView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.contacts.prefixed_id import ContactId, CustomerSegmentId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.contact_summaries import summarize_contact_row
from app.use_cases.shared.customer_segment_members import SegmentReaders

SEGMENT_ENTITY: AuditEntityName = AuditEntityName("customer_segment")
CONTACT_ENTITY: AuditEntityName = AuditEntityName("contact")
# Segments one business keeps at most.
MAX_SEGMENTS: int = 50


def authorize_owner(
    authorize: UseCaseContract[BusinessAccessRequest, BusinessDocument],
    user_id: UserId,
    business_id: BusinessId,
    access_mode: BusinessAccessMode | None = None,
) -> BusinessDocument:
    """Segments pick audiences and copy customers out: owners only."""

    return authorize.run(
        BusinessAccessRequest(
            user_id=user_id,
            business_id=business_id,
            required_role=BusinessMemberRole.OWNER,
            access_mode=access_mode,
        )
    )


def require_segment(
    segment_repo: CustomerSegmentRepoContract,
    business_id: BusinessId,
    segment_id: CustomerSegmentId,
) -> CustomerSegmentDocument:
    segment: CustomerSegmentDocument | None = segment_repo.get(business_id, segment_id)
    if segment is None:
        raise NotFoundError(f"Segment {segment_id} was not found.")

    return segment


def rules_of(body: SegmentRulesBody) -> SegmentRules:
    return SegmentRules(
        tag=body.tag,
        last_visit_days_ago=body.last_visit_days_ago,
        min_bookings=body.min_bookings,
        max_bookings=body.max_bookings,
        vip_only=body.vip_only,
    )


def segment_view(segment: CustomerSegmentDocument) -> SegmentView:
    rules: SegmentRules = segment.rules
    return SegmentView(
        id=segment.id,
        name=segment.name,
        rules=SegmentRulesBody(
            tag=rules.tag,
            last_visit_days_ago=rules.last_visit_days_ago,
            min_bookings=rules.min_bookings,
            max_bookings=rules.max_bookings,
            vip_only=rules.vip_only,
        ),
        created_at=segment.created_at,
        updated_at=segment.updated_at,
    )


def audit_entry(
    business_id: BusinessId,
    user_id: UserId,
    action: AuditAction,
    ip_address: ClientIpAddress | None,
    now: Microseconds,
    entity: AuditEntityName = SEGMENT_ENTITY,
    segment_id: CustomerSegmentId | None = None,
) -> AuditLogEntryDocument:
    return AuditLogEntryDocument(
        business_id=business_id,
        actor_id=user_id,
        action=action,
        entity=entity,
        entity_id=None if segment_id is None else AuditEntityReference(str(segment_id)),
        ip_address=ip_address,
        created_at=now,
        updated_at=now,
    )


@dataclass(frozen=True)
class MemberRows:
    """Members as the list shows them, their counts read in one aggregation."""

    readers: SegmentReaders

    def summarize(
        self, business_id: BusinessId, members: list[ContactDocument]
    ) -> list[ContactSummaryView]:
        totals: dict[ContactId, ContactActivityTotals] = (
            self.readers.activity_repo.count_for_contacts(
                business_id, [member.id for member in members]
            )
        )
        return [
            summarize_contact_row(member, totals.get(member.id)) for member in members
        ]
