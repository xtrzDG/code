"""Cabinet /channels helpers: checking a Telegram token, staff templates."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.channels.telegram_token_checks import (
    TelegramBotCheckView,
    TelegramTokenCheckRequest,
    ValidateTelegramTokenCommand,
)
from app.schemas.dto.staff_reply_templates import (
    SetWhatsAppStaffTemplatesCommand,
    WhatsAppStaffTemplatesRequest,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_token_check_body = build_json_body_dependency(TelegramTokenCheckRequest)
read_staff_templates_body = build_json_body_dependency(WhatsAppStaffTemplatesRequest)


def build_channel_setup_router(
    current_user: CurrentUserDependency,
    validate_telegram_token_operator: OperatorContract[
        ValidateTelegramTokenCommand, TelegramBotCheckView
    ],
    set_whatsapp_staff_templates_operator: OperatorContract[
        SetWhatsAppStaffTemplatesCommand, ChannelView
    ],
) -> APIRouter:
    """
    Routes (owners, bearer token):
        POST /v1/businesses/{business_id}/channels/telegram/validate-token
             {bot_token} -> the bot it opens (username, name, photo);
             nothing is saved
        PUT  /v1/businesses/{business_id}/channels/whatsapp/staff-templates
             {templates: [{name, language_code}]} -> the WhatsApp channel
             with its templates for staff replies, one per language
    """

    router = APIRouter(tags=["channels"], responses=standard_error_responses())

    @router.post(
        "/v1/businesses/{business_id}/channels/telegram/validate-token",
        openapi_extra=describe_json_body(TelegramTokenCheckRequest),
    )
    def validate_telegram_token(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[TelegramTokenCheckRequest, Depends(read_token_check_body)],
    ) -> TelegramBotCheckView:
        return validate_telegram_token_operator.operate(
            ValidateTelegramTokenCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
            )
        )

    @router.put(
        "/v1/businesses/{business_id}/channels/whatsapp/staff-templates",
        openapi_extra=describe_json_body(WhatsAppStaffTemplatesRequest),
    )
    def set_whatsapp_staff_templates(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            WhatsAppStaffTemplatesRequest, Depends(read_staff_templates_body)
        ],
    ) -> ChannelView:
        return set_whatsapp_staff_templates_operator.operate(
            SetWhatsAppStaffTemplatesCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
