"""Webhooks of messaging channels and the public website chat widget."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from fastapi.responses import PlainTextResponse

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
    read_raw_request_body,
)
from app.gateways.http.widget_cors_middleware import (
    WIDGET_CORS_HEADERS,
    WIDGET_SESSION_KEY_HEADER,
)
from app.schemas.dto.channels.channel_webhooks import (
    ChannelWebhookOutcome,
    ChannelWebhookPayload,
    MetaWebhookRequest,
    MetaWebhookVerificationRequest,
    TelegramWebhookRequest,
)
from app.schemas.dto.channels.staff_links import (
    PlatformBotWebhookOutcome,
    PlatformBotWebhookRequest,
)
from app.schemas.dto.channels.widget import (
    WidgetConfigView,
    WidgetMessageCommand,
    WidgetMessageRequest,
    WidgetMessagesQuery,
    WidgetMessagesView,
    WidgetReplyView,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetSessionKey
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import (
    MetaWebhookChallenge,
    MetaWebhookMode,
    PresentedWebhookSecret,
    WebhookSignatureHeader,
)
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.utilities.channels.channel_endpoints import (
    META_SIGNATURE_HEADER,
    META_WEBHOOK_PATH,
    TELEGRAM_PLATFORM_WEBHOOK_PATH,
    TELEGRAM_SECRET_HEADER,
    TELEGRAM_WEBHOOK_PATH_TEMPLATE,
)

WIDGET_CONFIG_PATH: str = "/v1/widget/{business_id}/config"
WIDGET_MESSAGES_PATH: str = "/v1/widget/{business_id}/messages"

read_widget_message_body = build_json_body_dependency(WidgetMessageRequest)


def build_channel_router(
    telegram_webhook_operator: OperatorContract[
        TelegramWebhookRequest,
        ChannelWebhookOutcome,
    ],
    meta_webhook_verification_operator: OperatorContract[
        MetaWebhookVerificationRequest,
        MetaWebhookChallenge,
    ],
    meta_webhook_operator: OperatorContract[MetaWebhookRequest, ChannelWebhookOutcome],
    platform_bot_webhook_operator: OperatorContract[
        PlatformBotWebhookRequest,
        PlatformBotWebhookOutcome,
    ],
    widget_config_operator: OperatorContract[BusinessId, WidgetConfigView],
    widget_message_operator: OperatorContract[WidgetMessageCommand, WidgetReplyView],
    widget_messages_operator: OperatorContract[
        WidgetMessagesQuery,
        WidgetMessagesView,
    ],
) -> APIRouter:
    """
    Routes (no bearer token; each is authenticated by its platform):
        POST /v1/channels/telegram/{channel_id}/webhook   business bot updates
        GET  /v1/channels/meta/webhook                    Meta verification
        POST /v1/channels/meta/webhook                    WhatsApp, Messenger,
                                                          Instagram messages
        POST /v1/channels/telegram-platform/webhook       staff bot updates
        GET  /v1/widget/{business_id}/config              public widget config
        POST /v1/widget/{business_id}/messages            widget visitor message
        GET  /v1/widget/{business_id}/messages            new assistant and staff
                                                          messages (header
                                                          X-Widget-Session-Key,
                                                          ?after=<message id>)
    """

    router = APIRouter(tags=["channels"], responses=standard_error_responses())

    @router.post(TELEGRAM_WEBHOOK_PATH_TEMPLATE)
    def receive_telegram_webhook(
        channel_id: str,
        body: Annotated[bytes, Depends(read_raw_request_body)],
        secret_token: Annotated[
            str | None,
            Header(alias=TELEGRAM_SECRET_HEADER),
        ] = None,
    ) -> ChannelWebhookOutcome:
        return telegram_webhook_operator.operate(
            TelegramWebhookRequest(
                channel_id=parse_path_identifier(channel_id, ChannelId, "Channel"),
                payload=build_payload(body, secret_token),
            )
        )

    @router.get(META_WEBHOOK_PATH, response_class=PlainTextResponse)
    def verify_meta_webhook(
        mode: Annotated[str | None, Query(alias="hub.mode")] = None,
        verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
        challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
    ) -> PlainTextResponse:
        verified_challenge: MetaWebhookChallenge = (
            meta_webhook_verification_operator.operate(
                MetaWebhookVerificationRequest(
                    mode=None if mode is None else MetaWebhookMode(mode),
                    verify_token=(
                        None
                        if verify_token is None
                        else PresentedWebhookSecret(verify_token)
                    ),
                    challenge=(
                        None if challenge is None else MetaWebhookChallenge(challenge)
                    ),
                )
            )
        )
        return PlainTextResponse(str(verified_challenge))

    @router.post(META_WEBHOOK_PATH)
    def receive_meta_webhook(
        body: Annotated[bytes, Depends(read_raw_request_body)],
        signature: Annotated[str | None, Header(alias=META_SIGNATURE_HEADER)] = None,
    ) -> ChannelWebhookOutcome:
        return meta_webhook_operator.operate(
            MetaWebhookRequest(payload=build_payload(body, signature))
        )

    @router.post(TELEGRAM_PLATFORM_WEBHOOK_PATH)
    def receive_platform_bot_webhook(
        body: Annotated[bytes, Depends(read_raw_request_body)],
        secret_token: Annotated[
            str | None,
            Header(alias=TELEGRAM_SECRET_HEADER),
        ] = None,
    ) -> PlatformBotWebhookOutcome:
        return platform_bot_webhook_operator.operate(
            PlatformBotWebhookRequest(payload=build_payload(body, secret_token))
        )

    @router.options(WIDGET_CONFIG_PATH, include_in_schema=False)
    @router.options(WIDGET_MESSAGES_PATH, include_in_schema=False)
    def allow_widget_preflight(business_id: str) -> Response:
        del business_id
        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
            headers=WIDGET_CORS_HEADERS,
        )

    @router.get(WIDGET_CONFIG_PATH)
    def get_widget_config(business_id: str, response: Response) -> WidgetConfigView:
        response.headers.update(WIDGET_CORS_HEADERS)
        return widget_config_operator.operate(
            parse_path_identifier(business_id, BusinessId, "Chat")
        )

    @router.post(
        WIDGET_MESSAGES_PATH,
        openapi_extra=describe_json_body(WidgetMessageRequest),
    )
    def send_widget_message(
        request: Request,
        business_id: str,
        response: Response,
        body: Annotated[WidgetMessageRequest, Depends(read_widget_message_body)],
    ) -> WidgetReplyView:
        response.headers.update(WIDGET_CORS_HEADERS)
        return widget_message_operator.operate(
            WidgetMessageCommand(
                business_id=parse_path_identifier(business_id, BusinessId, "Chat"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(WIDGET_MESSAGES_PATH)
    def list_widget_messages(
        request: Request,
        business_id: str,
        response: Response,
        session_key: Annotated[str, Header(alias=WIDGET_SESSION_KEY_HEADER)],
        after: Annotated[str | None, Query()] = None,
    ) -> WidgetMessagesView:
        response.headers.update(WIDGET_CORS_HEADERS)
        return widget_messages_operator.operate(
            WidgetMessagesQuery(
                business_id=parse_path_identifier(business_id, BusinessId, "Chat"),
                session_key=parse_session_key(session_key),
                after=parse_message_cursor(after),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router


def parse_session_key(raw_session_key: str) -> WidgetSessionKey:
    try:
        return WidgetSessionKey(raw_session_key)
    except ValueError as error:
        raise ValidationFailedError(
            "X-Widget-Session-Key must be the widget's visitor key."
        ) from error


def parse_message_cursor(raw_after: str | None) -> MessageId | None:
    """`after` is a message id the widget got from the API; blank means none."""

    if raw_after is None or raw_after.strip() == "":
        return None

    try:
        return MessageId(raw_after.strip())
    except ValueError as error:
        raise ValidationFailedError(
            "after must be a message id from an earlier answer."
        ) from error


def build_payload(body: bytes, signature_header: str | None) -> ChannelWebhookPayload:
    return ChannelWebhookPayload(
        body=body,
        signature_header=(
            None
            if signature_header is None
            else WebhookSignatureHeader(signature_header)
        ),
    )
