"""The team inbox: its views and counts, assignment and auto-assignment."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.conversations.feed_query_values import parse_channel
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.inbox import InboxView
from app.schemas.dto.inbox.assignment import (
    AssignConversationCommand,
    AssignConversationRequest,
    ConversationAssignmentView,
)
from app.schemas.dto.inbox.inbox_settings import (
    InboxSettingsQuery,
    InboxSettingsRequest,
    InboxSettingsView,
    UpdateInboxSettingsCommand,
)
from app.schemas.dto.inbox.inbox_views import (
    InboxAssigneeList,
    InboxAssigneesQuery,
    InboxPage,
    InboxQuery,
    InboxViewCounts,
    InboxViewCountsQuery,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.users.prefixed_id import UserId

read_assign_body = build_json_body_dependency(AssignConversationRequest)
read_settings_body = build_json_body_dependency(InboxSettingsRequest)


def build_inbox_router(
    current_user: CurrentUserDependency,
    list_inbox_operator: OperatorContract[InboxQuery, InboxPage],
    count_inbox_views_operator: OperatorContract[InboxViewCountsQuery, InboxViewCounts],
    list_inbox_assignees_operator: OperatorContract[
        InboxAssigneesQuery, InboxAssigneeList
    ],
    assign_conversation_operator: OperatorContract[
        AssignConversationCommand, ConversationAssignmentView
    ],
    get_inbox_settings_operator: OperatorContract[
        InboxSettingsQuery, InboxSettingsView
    ],
    update_inbox_settings_operator: OperatorContract[
        UpdateInboxSettingsCommand, InboxSettingsView
    ],
) -> APIRouter:
    """
    Routes (all require a bearer token; owners and staff unless noted):
        GET  /v1/businesses/{business_id}/inbox?view=&channel=&limit=&cursor=
                                    one page of a view (needs_person,
                                    requests, mine, unassigned, all; default
                                    all), the latest message first, with the
                                    views' counts (audited per viewer)
        GET  /v1/businesses/{business_id}/inbox/counts
                                    the views' counts only (badges)
        GET  /v1/businesses/{business_id}/inbox/assignees
                                    members to assign, with their workload
        POST /v1/businesses/{business_id}/conversations/{conversation_id}/assign
                                    {assignee_user_id|null, expected_revision}:
                                    compare and set, 409 assignment_changed
        GET  /v1/businesses/{business_id}/inbox/settings
        PUT  /v1/businesses/{business_id}/inbox/settings
                                    auto-assignment (owners)
    """

    router = APIRouter(tags=["inbox"], responses=standard_error_responses())

    @router.get("/v1/businesses/{business_id}/inbox")
    def list_inbox(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        view: str | None = None,
        channel: str | None = None,
        limit: str | None = None,
        cursor: str | None = None,
    ) -> InboxPage:
        return list_inbox_operator.operate(
            InboxQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                view=parse_view(view),
                channel=parse_channel(channel),
                page=parse_page_request(limit, cursor),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get("/v1/businesses/{business_id}/inbox/counts")
    def count_inbox_views(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> InboxViewCounts:
        return count_inbox_views_operator.operate(
            InboxViewCountsQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.get("/v1/businesses/{business_id}/inbox/assignees")
    def list_inbox_assignees(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> InboxAssigneeList:
        return list_inbox_assignees_operator.operate(
            InboxAssigneesQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/conversations/{conversation_id}/assign",
        openapi_extra=describe_json_body(AssignConversationRequest),
    )
    def assign_conversation(
        request: Request,
        business_id: str,
        conversation_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[AssignConversationRequest, Depends(read_assign_body)],
    ) -> ConversationAssignmentView:
        return assign_conversation_operator.operate(
            AssignConversationCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                conversation_id=parse_path_identifier(
                    conversation_id, ConversationId, "Conversation"
                ),
                assignee_user_id=body.assignee_user_id,
                expected_revision=body.expected_revision,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get("/v1/businesses/{business_id}/inbox/settings")
    def get_inbox_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> InboxSettingsView:
        return get_inbox_settings_operator.operate(
            InboxSettingsQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.put(
        "/v1/businesses/{business_id}/inbox/settings",
        openapi_extra=describe_json_body(InboxSettingsRequest),
    )
    def update_inbox_settings(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[InboxSettingsRequest, Depends(read_settings_body)],
    ) -> InboxSettingsView:
        return update_inbox_settings_operator.operate(
            UpdateInboxSettingsCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router


def parse_view(raw_view: str | None) -> InboxView:
    """The `view` query value; empty means ALL, an unknown one is refused."""

    if raw_view is None or raw_view.strip() == "":
        return InboxView.ALL

    try:
        return InboxView(raw_view.strip().lower())
    except ValueError as error:
        known_views: str = ", ".join(view.value for view in InboxView)
        raise ValidationFailedError(f"view must be one of: {known_views}.") from error
