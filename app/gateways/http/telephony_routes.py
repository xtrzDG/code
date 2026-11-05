"""The telephony line's call notifications (Zadarma PBX)."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import PlainTextResponse

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import read_raw_request_body
from app.schemas.dto.calls.missed_calls import (
    PbxCallWebhookOutcome,
    PbxCallWebhookRequest,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.strings import WebhookSignatureHeader

ZADARMA_NOTIFICATIONS_PATH: str = "/v1/telephony/zadarma/notifications"
ZADARMA_SIGNATURE_HEADER: str = "Signature"
# Zadarma checks the address with a random token it expects back as is.
ECHO_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def build_telephony_router(
    pbx_call_webhook_operator: OperatorContract[
        PbxCallWebhookRequest, PbxCallWebhookOutcome
    ],
) -> APIRouter:
    """
    Routes (no bearer token; Zadarma signs its notifications):
        GET  /v1/telephony/zadarma/notifications?zd_echo=…   address check
        POST /v1/telephony/zadarma/notifications             call notification

    The POST body is Zadarma's form (event, pbx_call_id, caller_id,
    called_did, disposition, duration, ...) with the `Signature` header. A
    NOTIFY_END of a call the line did not put through becomes a missed
    call with its text-back; every other notification is acknowledged and
    ignored.
    """

    router = APIRouter(tags=["telephony"], responses=standard_error_responses())

    @router.get(ZADARMA_NOTIFICATIONS_PATH, response_class=PlainTextResponse)
    def echo_zadarma_check(
        zd_echo: Annotated[str | None, Query()] = None,
    ) -> PlainTextResponse:
        if zd_echo is None or not ECHO_PATTERN.fullmatch(zd_echo):
            raise ValidationFailedError("zd_echo must be Zadarma's check token.")

        return PlainTextResponse(zd_echo)

    @router.post(ZADARMA_NOTIFICATIONS_PATH)
    def receive_zadarma_notification(
        body: Annotated[bytes, Depends(read_raw_request_body)],
        signature: Annotated[str | None, Header(alias=ZADARMA_SIGNATURE_HEADER)] = None,
    ) -> PbxCallWebhookOutcome:
        return pbx_call_webhook_operator.operate(
            PbxCallWebhookRequest(
                body=body,
                signature_header=(
                    None if signature is None else WebhookSignatureHeader(signature)
                ),
            )
        )

    return router
