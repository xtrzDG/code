"""The call fallback of rented numbers (Twilio's VoiceFallbackUrl and its dial)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import Response

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_raw_request_body,
)
from app.schemas.dto.calls.call_fallback import (
    CallFallbackReply,
    CallFallbackWebhookRequest,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import WebhookSignatureHeader
from app.utilities.calls.twilio_voice_webhooks import (
    TWILIO_FALLBACK_DIAL_PATH_TEMPLATE,
    TWILIO_SIGNATURE_HEADER,
    TWILIO_VOICE_FALLBACK_PATH_TEMPLATE,
)


class TwimlResponse(Response):
    """Twilio's instructions for the call (TwiML)."""

    media_type = "text/xml"


def build_twilio_voice_router(
    call_fallback_operator: OperatorContract[
        CallFallbackWebhookRequest, CallFallbackReply
    ],
    fallback_dial_operator: OperatorContract[
        CallFallbackWebhookRequest, CallFallbackReply
    ],
) -> APIRouter:
    """
    Routes (no bearer token; Twilio signs every request, its address with
    the business included, with the account's auth token in
    `X-Twilio-Signature`):
        POST /v1/telephony/twilio/voice-fallback/{business_id}
        POST /v1/telephony/twilio/voice-fallback/{business_id}/dial-status

    The business's rented numbers' VoiceFallbackUrl (each runs in that
    business's storage scope): when the voice platform could not
    take a call, the caller is put through to the staff mobile on duty
    (TwiML <Dial>, whose end Twilio reports to the second route) and the
    owner is told; with nobody to take it, or when the mobile does not
    answer, the call ends as a missed call with its text-back. Both answer
    TwiML (text/xml).
    """

    router = APIRouter(tags=["telephony"], responses=standard_error_responses())

    def request_of(
        raw_business_id: str, body: bytes, signature: str | None
    ) -> CallFallbackWebhookRequest:
        return CallFallbackWebhookRequest(
            business_id=parse_path_identifier(raw_business_id, BusinessId, "Business"),
            body=body,
            signature_header=(
                None if signature is None else WebhookSignatureHeader(signature)
            ),
        )

    @router.post(TWILIO_VOICE_FALLBACK_PATH_TEMPLATE, response_class=TwimlResponse)
    def receive_call_fallback(
        business_id: str,
        body: Annotated[bytes, Depends(read_raw_request_body)],
        signature: Annotated[str | None, Header(alias=TWILIO_SIGNATURE_HEADER)] = None,
    ) -> TwimlResponse:
        reply: CallFallbackReply = call_fallback_operator.operate(
            request_of(business_id, body, signature)
        )
        return TwimlResponse(str(reply.twiml))

    @router.post(TWILIO_FALLBACK_DIAL_PATH_TEMPLATE, response_class=TwimlResponse)
    def receive_fallback_dial_status(
        business_id: str,
        body: Annotated[bytes, Depends(read_raw_request_body)],
        signature: Annotated[str | None, Header(alias=TWILIO_SIGNATURE_HEADER)] = None,
    ) -> TwimlResponse:
        reply: CallFallbackReply = fallback_dial_operator.operate(
            request_of(business_id, body, signature)
        )
        return TwimlResponse(str(reply.twiml))

    return router
