from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.feedback.feedback_requests import (
    FeedbackRequestPage,
    FeedbackRequestPageQuery,
    FeedbackRequestView,
)
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.utilities.paging.keyset_paging import finish_page, read_slice

FEEDBACK_REQUEST_ENTITY: AuditEntityName = AuditEntityName("feedback_request")


class ListFeedbackRequestsUseCase(
    UseCaseContract[FeedbackRequestPageQuery, FeedbackRequestPage]
):
    """
    The visits asked about, newest first, one keyset page at a time
    (Settings → Reviews shows the last 20): the customer, whether and how
    they were asked or why not, their rating and whether they opened the
    review link. Owners only; the customers' names are personal data, so
    the view is audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        feedback_request_repo: FeedbackRequestRepoContract,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._feedback_request_repo: FeedbackRequestRepoContract = feedback_request_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: FeedbackRequestPageQuery) -> FeedbackRequestPage:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        fetched: list[FeedbackRequestDocument] = (
            self._feedback_request_repo.page_by_business(
                business.id, read_slice(input_data.page)
            )
        )
        items, next_cursor = finish_page(
            fetched,
            input_data.page,
            sort_key=lambda request: int(request.created_at),
            item_id=lambda request: str(request.id),
        )
        contacts: dict[ContactId, ContactDocument] = self._contact_repo.get_many(
            business.id, list({request.contact_id for request in items})
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.VIEW,
                entity=FEEDBACK_REQUEST_ENTITY,
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return FeedbackRequestPage(
            items=[
                build_feedback_request_view(request, contacts.get(request.contact_id))
                for request in items
            ],
            next_cursor=next_cursor,
        )


def build_feedback_request_view(
    request: FeedbackRequestDocument,
    contact: ContactDocument | None,
) -> FeedbackRequestView:
    return FeedbackRequestView(
        id=request.id,
        booking_id=request.booking_id,
        contact_id=request.contact_id,
        contact_name=None if contact is None else contact.name,
        visit_ended_at=request.visit_ended_at,
        status=request.status,
        skip_reason=request.skip_reason,
        channel=request.channel,
        sent_at=request.sent_at,
        score=request.score,
        answered_at=request.answered_at,
        review_clicks=request.review_clicks,
        conversation_id=request.conversation_id,
        last_error=request.last_error,
    )
