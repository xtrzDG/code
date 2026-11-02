"""Webhooks of the voice platform (ElevenLabs Agents)."""

import logging
from typing import Annotated

import anyio
import anyio.to_thread
from fastapi import APIRouter, Depends, Header, Response

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
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
    AccessDeniedError,
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
    CALLER_ID_BOUND_TOOLS,
    CAN_TRANSFER_VARIABLE,
    LOCAL_NOW_VARIABLE,
    NEXT_DAYS_VARIABLE,
    NO_TRANSFER_VALUE,
    OPEN_NOW_NO,
    OPEN_NOW_VARIABLE,
    OPEN_NOW_YES,
    TIMEZONE_VARIABLE,
    TRANSFER_NUMBER_VARIABLE,
)
from app.utilities.conversations.tool_payloads import render_tool_error

LOGGER: logging.Logger = logging.getLogger(__name__)
CALL_INITIATION_RESPONSE_TYPE: str = "conversation_initiation_client_data"
JSON_MEDIA_TYPE: str = "application/json"
# A caller waits in silence while a tool runs; ElevenLabs gives up after
# TOOL_RESPONSE_TIMEOUT_SECONDS (10 s). Past this deadline the agent hears
# that the system is slow, so it can tell the caller instead of hanging up.
VOICE_TOOL_DEADLINE_SECONDS: float = 8.0
VOICE_TOOL_TIMEOUT_MESSAGE: str = (
    "The booking system did not answer in time. Do not confirm or promise "
    "anything; tell the caller that a colleague will check and get back to them."
)


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
    body); the post-call webhook carries ElevenLabs-Signature. A tool call
    answers within VOICE_TOOL_DEADLINE_SECONDS: a tool still running then
    is left to finish on its own, and the agent gets an error result it
    can say to the caller. The tools that act on a customer's bookings by
    who they are (CALLER_ID_BOUND_TOOLS) never run on a call: a caller id
    proves nobody's identity, so once the webhook is authenticated the
    agent gets an error result that tells it to hand the request to staff.
    """

    router = APIRouter(tags=["voice"], responses=standard_error_responses())

    @router.post(VOICE_TOOL_PATH_TEMPLATE)
    async def run_voice_tool(
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
        request = VoiceToolWebhookRequest(
            tool_name=parse_tool_name(tool_name),
            credentials=build_credentials(business_id, tool_secret, body_signature),
            body=body,
        )
        result: VoiceToolCallResult | None = None
        with anyio.move_on_after(VOICE_TOOL_DEADLINE_SECONDS):
            try:
                result = await anyio.to_thread.run_sync(
                    voice_tool_operator.operate, request, abandon_on_cancel=True
                )
            except AccessDeniedError as refusal:
                if request.tool_name not in CALLER_ID_BOUND_TOOLS:
                    raise

                # Authenticated, and refused before it ran: the agent hears
                # why and hands the request to staff.
                return Response(
                    content=str(render_tool_error(str(refusal))),
                    media_type=JSON_MEDIA_TYPE,
                )

        if result is None:
            LOGGER.warning(
                "Voice tool %s did not finish within %.0f s",
                request.tool_name.value,
                VOICE_TOOL_DEADLINE_SECONDS,
            )
            return Response(
                content=str(render_tool_error(VOICE_TOOL_TIMEOUT_MESSAGE)),
                media_type=JSON_MEDIA_TYPE,
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
            "dynamic_variables": build_call_variables(initiation),
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


def build_call_variables(initiation: CallInitiationData) -> dict[str, str]:
    """
    The per-call variables of the agent's "Current call" block: whether the
    business is open and a transfer is possible, the local date and time,
    the next days and the time zone; and the staff number a transfer goes
    to ("none": no transfer on this call), read only by the transfer tool.
    """

    can_transfer: bool = initiation.transfer_phone_number is not None
    return {
        OPEN_NOW_VARIABLE: OPEN_NOW_YES if initiation.is_open_now else OPEN_NOW_NO,
        CAN_TRANSFER_VARIABLE: OPEN_NOW_YES if can_transfer else OPEN_NOW_NO,
        TRANSFER_NUMBER_VARIABLE: (
            NO_TRANSFER_VALUE
            if initiation.transfer_phone_number is None
            else str(initiation.transfer_phone_number)
        ),
        LOCAL_NOW_VARIABLE: str(initiation.local_now_text),
        NEXT_DAYS_VARIABLE: str(initiation.next_days_text),
        TIMEZONE_VARIABLE: str(initiation.timezone),
    }


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
