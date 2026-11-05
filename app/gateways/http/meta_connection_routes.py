"""Cabinet /channels: Meta's self-serve connection and Instagram comment-to-DM."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.channel_settings_routes import parse_channel_kind
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.channels.comment_replies import (
    InstagramCommentRepliesRequest,
    SetInstagramCommentRepliesCommand,
)
from app.schemas.dto.channels.meta_connection import (
    CompleteWhatsAppSignupCommand,
    CompleteWhatsAppSignupRequest,
    ConnectMetaPageCommand,
    ConnectMetaPageRequest,
    ListMetaPagesCommand,
    ListMetaPagesRequest,
    MetaConnectionStartView,
    MetaPageList,
    MetaSignInOptionsQuery,
    MetaSignInOptionsView,
    StartMetaConnectionCommand,
    StartMetaConnectionRequest,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

SIGN_IN_PATH: str = "/v1/businesses/{business_id}/channels/meta/sign-in"

read_start_body = build_json_body_dependency(StartMetaConnectionRequest)
read_signup_body = build_json_body_dependency(CompleteWhatsAppSignupRequest)
read_pages_body = build_json_body_dependency(ListMetaPagesRequest)
read_page_body = build_json_body_dependency(ConnectMetaPageRequest)
read_comment_replies_body = build_json_body_dependency(InstagramCommentRepliesRequest)


def build_meta_connection_router(
    current_user: CurrentUserDependency,
    sign_in_options_operator: OperatorContract[
        MetaSignInOptionsQuery, MetaSignInOptionsView
    ],
    start_meta_connection_operator: OperatorContract[
        StartMetaConnectionCommand, MetaConnectionStartView
    ],
    complete_whatsapp_signup_operator: OperatorContract[
        CompleteWhatsAppSignupCommand, ChannelView
    ],
    list_meta_pages_operator: OperatorContract[ListMetaPagesCommand, MetaPageList],
    connect_meta_page_operator: OperatorContract[ConnectMetaPageCommand, ChannelView],
    set_comment_replies_operator: OperatorContract[
        SetInstagramCommentRepliesCommand, ChannelView
    ],
) -> APIRouter:
    """
    Routes (all require a bearer token; changes are the owner's):
        GET  /v1/businesses/{business_id}/channels/meta/sign-in
                    which Facebook sign-ins the page offers (any member)
        POST /v1/businesses/{business_id}/channels/meta/sign-in
                    owner: start one ({purpose}: whatsapp or pages); the
                    one-time state and what the Facebook SDK opens with
        POST /v1/businesses/{business_id}/channels/whatsapp/embedded-signup
                    owner: finish WhatsApp Embedded Signup ({state, code,
                    whatsapp_business_account_id?, phone_number_id?})
        POST /v1/businesses/{business_id}/channels/meta/pages
                    owner: the pages of the page-picker sign-in ({state, code})
        PUT  /v1/businesses/{business_id}/channels/{channel}/page
                    owner: connect messenger or instagram with a picked page
                    ({state, page_id})
        PUT  /v1/businesses/{business_id}/channels/instagram/comment-replies
                    owner: Instagram comment-to-DM ({is_on, keywords,
                    reply_text})
    """

    router = APIRouter(tags=["channels"], responses=standard_error_responses())

    @router.get(SIGN_IN_PATH)
    def get_meta_sign_in_options(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> MetaSignInOptionsView:
        return sign_in_options_operator.operate(
            MetaSignInOptionsQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.post(
        SIGN_IN_PATH,
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(StartMetaConnectionRequest),
    )
    def start_meta_sign_in(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[StartMetaConnectionRequest, Depends(read_start_body)],
    ) -> MetaConnectionStartView:
        return start_meta_connection_operator.operate(
            StartMetaConnectionCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/channels/whatsapp/embedded-signup",
        openapi_extra=describe_json_body(CompleteWhatsAppSignupRequest),
    )
    def complete_whatsapp_embedded_signup(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CompleteWhatsAppSignupRequest, Depends(read_signup_body)],
    ) -> ChannelView:
        return complete_whatsapp_signup_operator.operate(
            CompleteWhatsAppSignupCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/channels/meta/pages",
        openapi_extra=describe_json_body(ListMetaPagesRequest),
    )
    def list_meta_pages(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ListMetaPagesRequest, Depends(read_pages_body)],
    ) -> MetaPageList:
        return list_meta_pages_operator.operate(
            ListMetaPagesCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
            )
        )

    @router.put(
        "/v1/businesses/{business_id}/channels/{channel}/page",
        openapi_extra=describe_json_body(ConnectMetaPageRequest),
    )
    def connect_meta_page(
        request: Request,
        business_id: str,
        channel: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ConnectMetaPageRequest, Depends(read_page_body)],
    ) -> ChannelView:
        return connect_meta_page_operator.operate(
            ConnectMetaPageCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                channel=parse_channel_kind(channel),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.put(
        "/v1/businesses/{business_id}/channels/instagram/comment-replies",
        openapi_extra=describe_json_body(InstagramCommentRepliesRequest),
    )
    def set_instagram_comment_replies(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            InstagramCommentRepliesRequest, Depends(read_comment_replies_body)
        ],
    ) -> ChannelView:
        return set_comment_replies_operator.operate(
            SetInstagramCommentRepliesCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
