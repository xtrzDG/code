"""Webhooks of the voice platform (ElevenLabs Agents)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.strict_request_parsing import read_raw_request_body
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.conversations import VoiceToolCallResult
from app.schemas.dto.voice_webhooks import (
    CallInitiationData,
    CallInitiationWebhookRequest,
    PostCallWebhookOutcome,
    PostCallWebhookRequest,
    VoiceToolWebhookRequest,
    VoiceWebhookCredentials,
)
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    NotFoundError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import (
    PresentedWebhookSecret,
    WebhookSignatureHeader,
)
from app.utilities.channels.channel_endpoints import (
    ELEVENLABS_SIGNATURE_HEADER,
    VOICE_BODY_SIGNATURE_HEADER,
    VOICE_BUSINESS_ID_HEADER,
    VOICE_CALL_INITIATION_PATH,
    VOICE_POST_CALL_PATH,
    VOICE_TOOL_PATH_TEMPLATE,
    VOICE_TOOL_SECRET_HEADER,
)
from app.utilities.channels.language_codes import to_voice_platform_language
from app.utilities.channels.voice_service import (
    OPEN_NOW_NO,
    OPEN_NOW_VARIABLE,
    OPEN_NOW_YES,
)

CALL_INITIATION_RESPONSE_TYPE: str = "conversation_initiation_client_data"
JSON_MEDIA_TYPE: str = "application/json"


def build_voice_router(
    voice_tool_operator: OperatorContract[VoiceToolWebhookRequest, VoiceToolCallResult],
    call_initiation_operator: OperatorContract[
        CallInitiationWebhookRequest,
        CallInitiationData,
    ],
    post_call_operator: OperatorContract[
        PostCallWebhookRequest, PostCallWebhookOutcome
    ],
) -> APIRouter:
    """
    Routes (no bearer token):
        POST /v1/voice/tools/{tool_name}                 agent tool call
        POST /v1/voice/webhooks/conversation-initiation  greeting of a call
        POST /v1/voice/webhooks/post-call                finished call

    Tool calls and call initiation carry X-Assistant-Business-Id and either
    X-Assistant-Tool-Secret or X-Assistant-Signature (sha256=HMAC of the
    body); the post-call webhook carries ElevenLabs-Signature.
    """

    router = APIRouter(tags=["voice"])

    @router.post(VOICE_TOOL_PATH_TEMPLATE)
    def run_voice_tool(
        tool_name: str,
        body: Annotated[bytes, Depends(read_raw_request_body)],
        business_id: Annotated[
            str | None,
            Header(alias=VOICE_BUSINESS_ID_HEADER),
        ] = None,
        tool_secret: Annotated[
            str | None,
            Header(alias=VOICE_TOOL_SECRET_HEADER),
        ] = None,
        body_signature: Annotated[
            str | None,
            Header(alias=VOICE_BODY_SIGNATURE_HEADER),
        ] = None,
    ) -> Response:
        result: VoiceToolCallResult = voice_tool_operator.operate(
            VoiceToolWebhookRequest(
                tool_name=parse_tool_name(tool_name),
                credentials=build_credentials(business_id, tool_secret, body_signature),
                body=body,
            )
        )
        return Response(content=str(result.result_json), media_type=JSON_MEDIA_TYPE)

    @router.post(VOICE_CALL_INITIATION_PATH)
    def start_voice_call(
        body: Annotated[bytes, Depends(read_raw_request_body)],
        business_id: Annotated[
            str | None,
            Header(alias=VOICE_BUSINESS_ID_HEADER),
        ] = None,
        tool_secret: Annotated[
            str | None,
            Header(alias=VOICE_TOOL_SECRET_HEADER),
        ] = None,
        body_signature: Annotated[
            str | None,
            Header(alias=VOICE_BODY_SIGNATURE_HEADER),
        ] = None,
    ) -> dict[str, object]:
        initiation: CallInitiationData = call_initiation_operator.operate(
            CallInitiationWebhookRequest(
                credentials=build_credentials(business_id, tool_secret, body_signature),
                body=body,
            )
        )
        return {
            "type": CALL_INITIATION_RESPONSE_TYPE,
            "conversation_config_override": {
                "agent": {
                    "first_message": str(initiation.first_message),
                    "language": to_voice_platform_language(initiation.language),
                }
            },
            "dynamic_variables": {
                OPEN_NOW_VARIABLE: (
                    OPEN_NOW_YES if initiation.is_open_now else OPEN_NOW_NO
                )
            },
        }

    @router.post(VOICE_POST_CALL_PATH)
    def receive_post_call(
        body: Annotated[bytes, Depends(read_raw_request_body)],
        signature: Annotated[
            str | None,
            Header(alias=ELEVENLABS_SIGNATURE_HEADER),
        ] = None,
    ) -> PostCallWebhookOutcome:
        return post_call_operator.operate(
            PostCallWebhookRequest(
                body=body,
                signature_header=(
                    None if signature is None else WebhookSignatureHeader(signature)
                ),
            )
        )

    return router


def parse_tool_name(raw_tool_name: str) -> AssistantToolName:
    try:
        return AssistantToolName(raw_tool_name)
    except ValueError as error:
        raise NotFoundError("This tool does not exist.") from error


def build_credentials(
    raw_business_id: str | None,
    tool_secret: str | None,
    body_signature: str | None,
) -> VoiceWebhookCredentials:
    """Credentials from headers; a missing or malformed business id is refused."""

    # A missing id must be refused here: BusinessId(None) would make a new one.
    if raw_business_id is None:
        raise AuthenticationRequiredError(f"{VOICE_BUSINESS_ID_HEADER} is missing.")

    try:
        business_id = BusinessId(raw_business_id)
    except (ValueError, TypeError) as error:
        raise AuthenticationRequiredError(
            f"{VOICE_BUSINESS_ID_HEADER} is malformed."
        ) from error

    return VoiceWebhookCredentials(
        business_id=business_id,
        tool_secret=None
        if tool_secret is None
        else PresentedWebhookSecret(tool_secret),
        body_signature=(
            None if body_signature is None else WebhookSignatureHeader(body_signature)
        ),
    )
