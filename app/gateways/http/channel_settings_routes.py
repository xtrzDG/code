"""Cabinet /channels: connected channels, widget code, staff Telegram links."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.channels import (
    ChannelListQuery,
    ChannelView,
    ConnectChannelCommand,
    ConnectChannelRequest,
    CreateTelegramLinkCommand,
    DisableChannelCommand,
    TelegramLinkRequest,
    TelegramLinkView,
    WidgetSnippetQuery,
    WidgetSnippetView,
)
from app.schemas.dto.staff_reply_templates import (
    SetWhatsAppStaffTemplateCommand,
    WhatsAppStaffTemplateRequest,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

# "web" is the short name of the website chat in the cabinet's addresses.
CHANNEL_PATH_ALIASES: dict[str, ChannelKind] = {"web": ChannelKind.WEB_CHAT}

read_connect_channel_body = build_json_body_dependency(ConnectChannelRequest)
read_telegram_link_body = build_json_body_dependency(TelegramLinkRequest)
read_staff_template_body = build_json_body_dependency(WhatsAppStaffTemplateRequest)


def build_channel_settings_router(
    list_channels_operator: OperatorContract[ChannelListQuery, list[ChannelView]],
    connect_channel_operator: OperatorContract[ConnectChannelCommand, ChannelView],
    disable_channel_operator: OperatorContract[DisableChannelCommand, ChannelView],
    widget_snippet_operator: OperatorContract[WidgetSnippetQuery, WidgetSnippetView],
    create_telegram_link_operator: OperatorContract[
        CreateTelegramLinkCommand,
        TelegramLinkView,
    ],
    current_user: CurrentUserDependency,
    set_whatsapp_staff_template_operator: OperatorContract[
        SetWhatsAppStaffTemplateCommand,
        ChannelView,
    ],
) -> APIRouter:
    """
    Routes (all require a bearer token):
        GET    /v1/businesses/{business_id}/channels               channels
        PUT    /v1/businesses/{business_id}/channels/{channel}     owner: connect
        DELETE /v1/businesses/{business_id}/channels/{channel}     owner: disable
        GET    /v1/businesses/{business_id}/channels/web/snippet   widget code
        PUT    /v1/businesses/{business_id}/channels/whatsapp/staff-template
                                                     owner: {name, language_code}
                                                     of the template for staff
                                                     replies after 24 hours
        POST   /v1/businesses/{business_id}/manager-contacts/telegram-link
                                                     owner: staff Telegram code

    `channel` is telegram, whatsapp, instagram, messenger, phone or web
    (web_chat). Credentials are never returned.
    """

    router = APIRouter(tags=["channels"])

    @router.get("/v1/businesses/{business_id}/channels")
    def list_channels(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> list[ChannelView]:
        return list_channels_operator.operate(
            ChannelListQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.get("/v1/businesses/{business_id}/channels/web/snippet")
    def get_widget_snippet(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> WidgetSnippetView:
        return widget_snippet_operator.operate(
            WidgetSnippetQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.put(
        "/v1/businesses/{business_id}/channels/{channel}",
        openapi_extra=describe_json_body(ConnectChannelRequest),
    )
    def connect_channel(
        request: Request,
        business_id: str,
        channel: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ConnectChannelRequest, Depends(read_connect_channel_body)],
    ) -> ChannelView:
        return connect_channel_operator.operate(
            ConnectChannelCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                channel=parse_channel_kind(channel),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.put(
        "/v1/businesses/{business_id}/channels/whatsapp/staff-template",
        openapi_extra=describe_json_body(WhatsAppStaffTemplateRequest),
    )
    def set_whatsapp_staff_template(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            WhatsAppStaffTemplateRequest, Depends(read_staff_template_body)
        ],
    ) -> ChannelView:
        return set_whatsapp_staff_template_operator.operate(
            SetWhatsAppStaffTemplateCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete("/v1/businesses/{business_id}/channels/{channel}")
    def disable_channel(
        request: Request,
        business_id: str,
        channel: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ChannelView:
        return disable_channel_operator.operate(
            DisableChannelCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                channel=parse_channel_kind(channel),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/manager-contacts/telegram-link",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(TelegramLinkRequest),
    )
    def create_telegram_link(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[TelegramLinkRequest, Depends(read_telegram_link_body)],
    ) -> TelegramLinkView:
        return create_telegram_link_operator.operate(
            CreateTelegramLinkCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router


def parse_channel_kind(raw_channel: str) -> ChannelKind:
    """A channel named in the path; unknown names are not found."""

    alias: ChannelKind | None = CHANNEL_PATH_ALIASES.get(raw_channel)
    if alias is not None:
        return alias

    try:
        return ChannelKind(raw_channel)
    except ValueError as error:
        raise NotFoundError("Channel was not found.") from error
