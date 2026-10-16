"""Teaching the assistant from its answers: "Fix this answer" and the
Overview's answers worth improving."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.conversation_feed.answer_corrections import (
    AnswerCorrectionDraft,
    AnswerCorrectionQuery,
    AnswerCorrectionRequest,
    AnswerCorrectionResult,
    CorrectAnswerCommand,
)
from app.schemas.dto.conversation_feed.answers_to_improve import (
    DEFAULT_ANSWERS_TO_IMPROVE,
    AnswersToImproveQuery,
    AnswersToImproveView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_integers import (
    AnswersToImproveLimit,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.users.prefixed_id import UserId

read_correction_body = build_json_body_dependency(AnswerCorrectionRequest)
CORRECTION_PATH: str = (
    "/v1/businesses/{business_id}/conversations/{conversation_id}"
    "/messages/{message_id}/correction"
)


def build_answer_fix_router(
    current_user: CurrentUserDependency,
    get_correction_draft: OperatorContract[
        AnswerCorrectionQuery, AnswerCorrectionDraft
    ],
    correct_answer: OperatorContract[CorrectAnswerCommand, AnswerCorrectionResult],
    list_answers_to_improve: OperatorContract[
        AnswersToImproveQuery, AnswersToImproveView
    ],
) -> APIRouter:
    """
    Routes (all require a bearer token):
        GET  .../conversations/{conversation_id}/messages/{message_id}/correction
                                    what "Fix this answer" opens with: the
                                    customer's question, the suggested kind,
                                    the current fact (owner; audited)
        POST .../conversations/{conversation_id}/messages/{message_id}/correction
                                    {scope, question?, correct_answer?,
                                     knowledge_item_id?, price_minor?}: the
                                    correction as knowledge (owner)
        GET  /v1/businesses/{business_id}/answers-to-improve?limit=
                                    bad ratings nobody acted on, then
                                    questions without an answer
    """

    router = APIRouter(tags=["conversations"], responses=standard_error_responses())

    def ids(
        business_id: str, conversation_id: str, message_id: str
    ) -> tuple[BusinessId, ConversationId, MessageId]:
        return (
            parse_path_identifier(business_id, BusinessId, "Business"),
            parse_path_identifier(conversation_id, ConversationId, "Conversation"),
            parse_path_identifier(message_id, MessageId, "Message"),
        )

    @router.get(CORRECTION_PATH)
    def get_answer_correction_draft(
        request: Request,
        business_id: str,
        conversation_id: str,
        message_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AnswerCorrectionDraft:
        business, conversation, message = ids(business_id, conversation_id, message_id)
        return get_correction_draft.operate(
            AnswerCorrectionQuery(
                user_id=user_id,
                business_id=business,
                conversation_id=conversation,
                message_id=message,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        CORRECTION_PATH, openapi_extra=describe_json_body(AnswerCorrectionRequest)
    )
    def correct_assistant_answer(
        business_id: str,
        conversation_id: str,
        message_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[AnswerCorrectionRequest, Depends(read_correction_body)],
    ) -> AnswerCorrectionResult:
        business, conversation, message = ids(business_id, conversation_id, message_id)
        return correct_answer.operate(
            CorrectAnswerCommand(
                user_id=user_id,
                business_id=business,
                conversation_id=conversation,
                message_id=message,
                request=body,
            )
        )

    @router.get("/v1/businesses/{business_id}/answers-to-improve")
    def get_answers_to_improve(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        limit: str | None = None,
    ) -> AnswersToImproveView:
        return list_answers_to_improve.operate(
            AnswersToImproveQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                limit=parse_optional(
                    limit, lambda raw: AnswersToImproveLimit(int(raw)), "limit"
                )
                or DEFAULT_ANSWERS_TO_IMPROVE,
            )
        )

    return router
