from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.customer_repositories import (
    CustomerSegmentRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.customer_segments import CustomerSegmentDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.customers.customer_segments import (
    CreateSegmentCommand,
    SegmentView,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.use_cases.contacts.segments.segment_support import (
    MAX_SEGMENTS,
    audit_entry,
    authorize_owner,
    rules_of,
    segment_view,
)


class CreateSegmentUseCase(UseCaseContract[CreateSegmentCommand, SegmentView]):
    """
    The owner saves a segment by its rules (at most 50 per business).
    Owners only; audited (CREATE of customer_segment).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        segment_repo: CustomerSegmentRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._segment_repo: CustomerSegmentRepoContract = segment_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CreateSegmentCommand) -> SegmentView:
        """
        Raises:
            ConflictError: the business has the most segments it may keep.
        """

        business: BusinessDocument = authorize_owner(
            self._authorize_business_access, input_data.user_id, input_data.business_id
        )
        if len(self._segment_repo.list_by_business(business.id)) >= MAX_SEGMENTS:
            raise ConflictError(
                f"A business keeps at most {MAX_SEGMENTS} segments; delete one first."
            )

        now: Microseconds = self._wall_clock.now_unix()
        segment = CustomerSegmentDocument(
            business_id=business.id,
            name=input_data.request.name,
            rules=rules_of(input_data.request.rules),
            created_by=input_data.user_id,
            created_at=now,
            updated_at=now,
        )
        self._segment_repo.save(segment)
        self._audit_log_repo.append(
            audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.CREATE,
                input_data.client_ip_address,
                now,
                segment_id=segment.id,
            )
        )
        return segment_view(segment)
