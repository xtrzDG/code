"""Cabinet routes of what staff follow up: leads, handoffs and unanswered
questions."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.operations.business_access import (
    BUSINESS_PREFIX,
    BusinessAuthorizer,
)
from app.gateways.http.operations.query_values import (
    OptionalQuery,
    parse_flag,
    parse_optional_flag,
    parse_optional_text,
    parse_path_id,
)
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.bookings import LeadStatus
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.bookings import LeadView
from app.schemas.dto.operations.handoffs import (
    HandoffListItem,
    HandoffPage,
    ListHandoffsQuery,
    ReopenHandoffCommand,
    ResolveHandoffCommand,
)
from app.schemas.dto.operations.leads import (
    LeadPage,
    ListLeadsQuery,
    UpdateLeadStatusCommand,
    UpdateLeadStatusRequest,
)
from app.schemas.dto.operations.unanswered_questions import (
    AnsweredQuestionResult,
    AnswerUnansweredQuestionCommand,
    AnswerUnansweredQuestionRequest,
    ListUnansweredQuestionsQuery,
    UnansweredQuestionPage,
)
from app.schemas.typings.bookings.prefixed_id import LeadId
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.schemas.typings.users.prefixed_id import UserId

read_lead_status_body = build_json_body_dependency(UpdateLeadStatusRequest)
read_answer_body = build_json_body_dependency(AnswerUnansweredQuestionRequest)


def build_follow_up_routes(
    *,
    current_user: CurrentUserDependency,
    authorize: BusinessAuthorizer,
    list_leads: OperatorContract[ListLeadsQuery, LeadPage],
    update_lead_status: OperatorContract[UpdateLeadStatusCommand, LeadView],
    list_handoffs: OperatorContract[ListHandoffsQuery, HandoffPage],
    resolve_handoff: OperatorContract[ResolveHandoffCommand, HandoffListItem],
    reopen_handoff: OperatorContract[ReopenHandoffCommand, HandoffListItem],
    list_unanswered_questions: OperatorContract[
        ListUnansweredQuestionsQuery, UnansweredQuestionPage
    ],
    answer_unanswered_question: OperatorContract[
        AnswerUnansweredQuestionCommand, AnsweredQuestionResult
    ],
) -> APIRouter:
    """
    Leads, handoffs and unanswered questions under
    /v1/businesses/{business_id} (Bearer auth; owners and staff, answering a
    question only owners).
    """

    router = APIRouter()

    @router.get(f"{BUSINESS_PREFIX}/leads")
    def get_leads(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        status: OptionalQuery = None,
        include_sandbox: OptionalQuery = None,
        limit: OptionalQuery = None,
        cursor: OptionalQuery = None,
    ) -> LeadPage:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_leads.operate(
            ListLeadsQuery(
                business_id=business.id,
                actor_id=user_id,
                status=parse_optional_text(status, LeadStatus, "status"),
                include_sandbox=parse_flag(include_sandbox, "include_sandbox"),
                page=parse_page_request(limit, cursor),
            )
        )

    @router.patch(
        f"{BUSINESS_PREFIX}/leads/{{lead_id}}",
        openapi_extra=describe_json_body(UpdateLeadStatusRequest),
    )
    def patch_lead(
        business_id: str,
        lead_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[UpdateLeadStatusRequest, Depends(read_lead_status_body)],
    ) -> LeadView:
        business: BusinessDocument = authorize(user_id, business_id)
        return update_lead_status.operate(
            UpdateLeadStatusCommand(
                business_id=business.id,
                lead_id=parse_path_id(lead_id, LeadId, "Lead"),
                status=body.status,
            )
        )

    @router.get(f"{BUSINESS_PREFIX}/handoffs")
    def get_handoffs(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        status: OptionalQuery = None,
        is_open: OptionalQuery = None,
        include_sandbox: OptionalQuery = None,
        limit: OptionalQuery = None,
        cursor: OptionalQuery = None,
    ) -> HandoffPage:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_handoffs.operate(
            ListHandoffsQuery(
                business_id=business.id,
                actor_id=user_id,
                status=parse_optional_text(status, HandoffStatus, "status"),
                is_open=parse_optional_flag(is_open, "is_open"),
                include_sandbox=parse_flag(include_sandbox, "include_sandbox"),
                page=parse_page_request(limit, cursor),
            )
        )

    @router.post(f"{BUSINESS_PREFIX}/handoffs/{{handoff_id}}/resolve")
    def post_handoff_resolve(
        business_id: str,
        handoff_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> HandoffListItem:
        business: BusinessDocument = authorize(user_id, business_id)
        return resolve_handoff.operate(
            ResolveHandoffCommand(
                business_id=business.id,
                handoff_id=parse_path_id(handoff_id, HandoffId, "Handoff"),
                actor_id=user_id,
            )
        )

    @router.post(f"{BUSINESS_PREFIX}/handoffs/{{handoff_id}}/reopen")
    def post_handoff_reopen(
        business_id: str,
        handoff_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> HandoffListItem:
        """
        Open a resolved handoff again (the Undo of "Resolved"): it waits for
        a person and the assistant stays silent in its conversation again.
        """

        business: BusinessDocument = authorize(user_id, business_id)
        return reopen_handoff.operate(
            ReopenHandoffCommand(
                business_id=business.id,
                actor_id=user_id,
                handoff_id=parse_path_id(handoff_id, HandoffId, "Handoff"),
            )
        )

    @router.get(f"{BUSINESS_PREFIX}/unanswered-questions")
    def get_unanswered_questions(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        include_resolved: OptionalQuery = None,
        include_sandbox: OptionalQuery = None,
        limit: OptionalQuery = None,
        cursor: OptionalQuery = None,
    ) -> UnansweredQuestionPage:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_unanswered_questions.operate(
            ListUnansweredQuestionsQuery(
                business_id=business.id,
                include_resolved=parse_flag(include_resolved, "include_resolved"),
                include_sandbox=parse_flag(include_sandbox, "include_sandbox"),
                page=parse_page_request(limit, cursor),
            )
        )

    @router.post(
        f"{BUSINESS_PREFIX}/unanswered-questions/{{question_id}}/answer",
        openapi_extra=describe_json_body(AnswerUnansweredQuestionRequest),
    )
    def post_unanswered_question_answer(
        business_id: str,
        question_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[AnswerUnansweredQuestionRequest, Depends(read_answer_body)],
    ) -> AnsweredQuestionResult:
        business: BusinessDocument = authorize(
            user_id, business_id, BusinessMemberRole.OWNER
        )
        return answer_unanswered_question.operate(
            AnswerUnansweredQuestionCommand(
                business_id=business.id,
                question_id=parse_path_id(
                    question_id, UnansweredQuestionId, "Question"
                ),
                answer=body.answer,
                title=body.title,
            )
        )

    return router
