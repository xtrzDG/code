"""What the team writes in the inbox: internal notes and saved replies."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.inbox.conversation_notes import (
    ConversationNotePage,
    ConversationNoteRequest,
    ConversationNotesQuery,
    ConversationNoteView,
    CreateConversationNoteCommand,
    DeleteConversationNoteCommand,
    DeletedConversationNote,
)
from app.schemas.dto.inbox.quick_replies import (
    ConversationQuickRepliesQuery,
    DeleteQuickReplyCommand,
    FilledQuickReplyList,
    QuickRepliesQuery,
    QuickReplyList,
    QuickReplyRequest,
    QuickReplyView,
    SaveQuickReplyCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.inbox.prefixed_id import ConversationNoteId, QuickReplyId
from app.schemas.typings.users.prefixed_id import UserId

read_note_body = build_json_body_dependency(ConversationNoteRequest)
read_quick_reply_body = build_json_body_dependency(QuickReplyRequest)
CONVERSATION_PATH: str = "/v1/businesses/{business_id}/conversations/{conversation_id}"
QUICK_REPLIES_PATH: str = "/v1/businesses/{business_id}/quick-replies"


def build_inbox_content_router(
    current_user: CurrentUserDependency,
    create_note_operator: OperatorContract[
        CreateConversationNoteCommand, ConversationNoteView
    ],
    list_notes_operator: OperatorContract[ConversationNotesQuery, ConversationNotePage],
    delete_note_operator: OperatorContract[
        DeleteConversationNoteCommand, DeletedConversationNote
    ],
    list_quick_replies_operator: OperatorContract[QuickRepliesQuery, QuickReplyList],
    save_quick_reply_operator: OperatorContract[SaveQuickReplyCommand, QuickReplyView],
    delete_quick_reply_operator: OperatorContract[
        DeleteQuickReplyCommand, QuickReplyList
    ],
    fill_quick_replies_operator: OperatorContract[
        ConversationQuickRepliesQuery, FilledQuickReplyList
    ],
) -> APIRouter:
    """
    Routes (all require a bearer token; owners and staff unless noted):
        GET    .../conversations/{conversation_id}/notes?limit=&cursor=
                                    internal notes, newest first (audited)
        POST   .../conversations/{conversation_id}/notes {text}
                                    a note (audited; never sent to the
                                    customer or the model)
        DELETE .../conversations/{conversation_id}/notes/{note_id}
                                    the author's own note, or any for owners
        GET    .../conversations/{conversation_id}/quick-replies
                                    saved replies filled in for the
                                    conversation (audited)
        GET    /v1/businesses/{business_id}/quick-replies
        POST   /v1/businesses/{business_id}/quick-replies       (owners)
        PUT    /v1/businesses/{business_id}/quick-replies/{id}  (owners)
        DELETE /v1/businesses/{business_id}/quick-replies/{id}  (owners)
    """

    router = APIRouter(tags=["inbox"], responses=standard_error_responses())

    def business(business_id: str) -> BusinessId:
        return parse_path_identifier(business_id, BusinessId, "Business")

    def conversation(conversation_id: str) -> ConversationId:
        return parse_path_identifier(conversation_id, ConversationId, "Conversation")

    @router.get(f"{CONVERSATION_PATH}/notes")
    def list_conversation_notes(
        request: Request,
        business_id: str,
        conversation_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        limit: str | None = None,
        cursor: str | None = None,
    ) -> ConversationNotePage:
        return list_notes_operator.operate(
            ConversationNotesQuery(
                user_id=user_id,
                business_id=business(business_id),
                conversation_id=conversation(conversation_id),
                page=parse_page_request(limit, cursor),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        f"{CONVERSATION_PATH}/notes",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(ConversationNoteRequest),
    )
    def create_conversation_note(
        request: Request,
        business_id: str,
        conversation_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ConversationNoteRequest, Depends(read_note_body)],
    ) -> ConversationNoteView:
        return create_note_operator.operate(
            CreateConversationNoteCommand(
                user_id=user_id,
                business_id=business(business_id),
                conversation_id=conversation(conversation_id),
                text=body.text,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete(
        f"{CONVERSATION_PATH}/notes/{{note_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_conversation_note(
        request: Request,
        business_id: str,
        conversation_id: str,
        note_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        delete_note_operator.operate(
            DeleteConversationNoteCommand(
                user_id=user_id,
                business_id=business(business_id),
                conversation_id=conversation(conversation_id),
                note_id=parse_path_identifier(note_id, ConversationNoteId, "Note"),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(f"{CONVERSATION_PATH}/quick-replies")
    def fill_quick_replies(
        request: Request,
        business_id: str,
        conversation_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> FilledQuickReplyList:
        return fill_quick_replies_operator.operate(
            ConversationQuickRepliesQuery(
                user_id=user_id,
                business_id=business(business_id),
                conversation_id=conversation(conversation_id),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(QUICK_REPLIES_PATH)
    def list_quick_replies(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> QuickReplyList:
        return list_quick_replies_operator.operate(
            QuickRepliesQuery(user_id=user_id, business_id=business(business_id))
        )

    @router.post(
        QUICK_REPLIES_PATH,
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(QuickReplyRequest),
    )
    def create_quick_reply(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[QuickReplyRequest, Depends(read_quick_reply_body)],
    ) -> QuickReplyView:
        return save_quick_reply_operator.operate(
            SaveQuickReplyCommand(
                user_id=user_id,
                business_id=business(business_id),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.put(
        f"{QUICK_REPLIES_PATH}/{{quick_reply_id}}",
        openapi_extra=describe_json_body(QuickReplyRequest),
    )
    def update_quick_reply(
        request: Request,
        business_id: str,
        quick_reply_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[QuickReplyRequest, Depends(read_quick_reply_body)],
    ) -> QuickReplyView:
        return save_quick_reply_operator.operate(
            SaveQuickReplyCommand(
                user_id=user_id,
                business_id=business(business_id),
                quick_reply_id=parse_path_identifier(
                    quick_reply_id, QuickReplyId, "Saved reply"
                ),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete(
        f"{QUICK_REPLIES_PATH}/{{quick_reply_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_quick_reply(
        request: Request,
        business_id: str,
        quick_reply_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        delete_quick_reply_operator.operate(
            DeleteQuickReplyCommand(
                user_id=user_id,
                business_id=business(business_id),
                quick_reply_id=parse_path_identifier(
                    quick_reply_id, QuickReplyId, "Saved reply"
                ),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
