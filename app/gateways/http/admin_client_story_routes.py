"""
Platform admin: a client's story (R13): the platform team's notes, the
timeline, and the done-for-you setup marked done.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.admin_account_action_routes import CLIENT_PATH, client_id
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.admin import AdminClientQuery
from app.schemas.dto.admin_actions import AdminActionReceipt, CompleteOnboardingCommand
from app.schemas.dto.client_story import (
    ClientNoteBody,
    ClientNoteChange,
    ClientNoteList,
    ClientTimelinePage,
    ClientTimelineQuery,
    CreateClientNoteCommand,
    DeleteClientNoteCommand,
    UpdateClientNoteCommand,
)
from app.schemas.typings.client_health.prefixed_id import ClientNoteId
from app.schemas.typings.users.prefixed_id import UserId

read_note_body = build_json_body_dependency(ClientNoteBody)
read_note_change = build_json_body_dependency(ClientNoteChange)


def build_admin_client_story_router(
    list_notes_operator: OperatorContract[AdminClientQuery, ClientNoteList],
    create_note_operator: OperatorContract[CreateClientNoteCommand, ClientNoteList],
    update_note_operator: OperatorContract[UpdateClientNoteCommand, ClientNoteList],
    delete_note_operator: OperatorContract[DeleteClientNoteCommand, None],
    timeline_operator: OperatorContract[ClientTimelineQuery, ClientTimelinePage],
    complete_onboarding_operator: OperatorContract[
        CompleteOnboardingCommand, AdminActionReceipt
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (bearer token of a platform admin; writing notes and marking the
    setup done need SUPER or BILLING):
        GET    …/notes                    the notes, pinned first
        POST   …/notes                    {"text", "is_pinned"?}
        PATCH  …/notes/{note_id}          {"text"?, "is_pinned"?}
        DELETE …/notes/{note_id}          204
        GET    …/timeline?limit=&cursor=  the story, newest first
        POST   …/onboarding-request/done  the done-for-you setup is done
    (… is /v1/admin/clients/{business_id}).
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.get(f"{CLIENT_PATH}/notes")
    def list_notes(
        business_id: str, user_id: Annotated[UserId, Depends(current_user)]
    ) -> ClientNoteList:
        return list_notes_operator.operate(
            AdminClientQuery(user_id=user_id, business_id=client_id(business_id))
        )

    @router.post(
        f"{CLIENT_PATH}/notes",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(ClientNoteBody),
    )
    def create_note(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ClientNoteBody, Depends(read_note_body)],
    ) -> ClientNoteList:
        return create_note_operator.operate(
            CreateClientNoteCommand(
                user_id=user_id, business_id=client_id(business_id), body=body
            )
        )

    @router.patch(
        f"{CLIENT_PATH}/notes/{{note_id}}",
        openapi_extra=describe_json_body(ClientNoteChange),
    )
    def update_note(
        business_id: str,
        note_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ClientNoteChange, Depends(read_note_change)],
    ) -> ClientNoteList:
        return update_note_operator.operate(
            UpdateClientNoteCommand(
                user_id=user_id,
                business_id=client_id(business_id),
                note_id=parse_path_identifier(note_id, ClientNoteId, "Note"),
                body=body,
            )
        )

    @router.delete(
        f"{CLIENT_PATH}/notes/{{note_id}}", status_code=status.HTTP_204_NO_CONTENT
    )
    def delete_note(
        business_id: str,
        note_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        delete_note_operator.operate(
            DeleteClientNoteCommand(
                user_id=user_id,
                business_id=client_id(business_id),
                note_id=parse_path_identifier(note_id, ClientNoteId, "Note"),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(f"{CLIENT_PATH}/timeline")
    def get_timeline(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        limit: str | None = None,
        cursor: str | None = None,
    ) -> ClientTimelinePage:
        return timeline_operator.operate(
            ClientTimelineQuery(
                user_id=user_id,
                business_id=client_id(business_id),
                page=parse_page_request(limit, cursor),
            )
        )

    @router.post(f"{CLIENT_PATH}/onboarding-request/done")
    def complete_onboarding(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AdminActionReceipt:
        return complete_onboarding_operator.operate(
            CompleteOnboardingCommand(
                user_id=user_id,
                business_id=client_id(business_id),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
