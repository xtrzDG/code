"""A WhatsApp template Meta refuses is told apart from an outage."""

import httpx
import pytest

from app.clients.meta.meta_graph_client import MetaGraphClient
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    WhatsAppTemplateRejectedError,
)
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import ChannelSecret, OutboundMessagePart
from app.schemas.typings.conversations.strings import ChannelUserId


def send_template(status_code: int, error: dict[str, object]) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": error})

    MetaGraphClient(transport=httpx.MockTransport(handle)).send_whatsapp_template(
        ChannelSecret("system-user-token"),
        MetaObjectId("123456789012345"),
        ChannelUserId("5511961234567"),
        WhatsAppTemplateName("staff_reply"),
        WhatsAppTemplateLanguageCode("en"),
        [OutboundMessagePart("Your table is ready.")],
    )


@pytest.mark.parametrize(
    ("status_code", "code"),
    [(404, 132001), (400, 132000), (400, 132012), (400, 132015)],
)
def test_a_refused_template_is_a_template_rejection(
    status_code: int, code: int
) -> None:
    with pytest.raises(WhatsAppTemplateRejectedError, match=str(code)):
        send_template(
            status_code,
            {"code": code, "message": f"(#{code}) Template name does not exist"},
        )


def test_other_meta_errors_stay_service_errors() -> None:
    with pytest.raises(ExternalServiceError) as failure:
        send_template(400, {"code": 131000, "message": "Something went wrong"})

    assert not isinstance(failure.value, WhatsAppTemplateRejectedError)
