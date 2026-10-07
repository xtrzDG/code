"""The voice tool webhook: the agent's tool calls authenticated per business."""

import json
from typing import Any

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.channels.webhook_signatures import sign_body
from tests.channels.channels_payloads import HttpResponse, to_json_bytes
from tests.channels.channels_settings import ISRAEL, build_settings
from tests.channels.voice_setup import VoiceSetup, build_voice_setup, tool_secret


class TestVoiceToolWebhook:
    def call_tool(
        self,
        setup: VoiceSetup,
        tool_name: str,
        body: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        default_headers: dict[str, str] = {
            "X-Assistant-Business-Id": str(setup.business.id),
            "X-Assistant-Tool-Secret": tool_secret(setup.business.id),
        }
        return setup.testbed.build_http_client().post(
            f"/v1/voice/tools/{tool_name}",
            content=to_json_bytes(body),
            headers=default_headers if headers is None else headers,
        )

    def test_tool_call_runs_with_the_business_from_the_credentials(self) -> None:
        setup = build_voice_setup(country=ISRAEL)
        arguments = {"name": "דנה", "party_size": 2, "starts_at": "2026-10-03T19:30"}

        response = self.call_tool(
            setup,
            "create_booking",
            {
                "arguments": arguments,
                "conversation_id": "conv_9",
                "caller_id": "050-234-5678",
                "language": "he",
                "business_id": "business_of_someone_else",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"ok": True, "tool": "create_booking"}
        [request] = setup.testbed.voice_tool_orchestrator.requests
        assert request.business_id == setup.business.id
        assert request.provider_call_id == "conv_9"
        assert request.caller_phone_number == "+972502345678"
        assert request.tool_name is AssistantToolName.CREATE_BOOKING
        assert request.language == "he"
        assert json.loads(request.input_json) == arguments

    def test_body_signature_is_an_alternative_to_the_secret(self) -> None:
        setup = build_voice_setup()
        body = {"arguments": {"query": "parking"}, "conversation_id": "conv_1"}
        raw: bytes = to_json_bytes(body)
        signature = "sha256=" + sign_body(tool_secret(setup.business.id), raw)

        response = setup.testbed.build_http_client().post(
            "/v1/voice/tools/search_knowledge",
            content=raw,
            headers={
                "X-Assistant-Business-Id": str(setup.business.id),
                "X-Assistant-Signature": signature,
            },
        )

        assert response.status_code == 200
        [request] = setup.testbed.voice_tool_orchestrator.requests
        assert request.caller_phone_number is None
        assert request.language is None

    def test_flat_bodies_and_withheld_numbers(self) -> None:
        setup = build_voice_setup()

        self.call_tool(
            setup,
            "get_price",
            {
                "item_name": "VR hour",
                "conversation_id": "conv_1",
                "caller_id": "anonymous",
            },
        )

        [request] = setup.testbed.voice_tool_orchestrator.requests
        assert json.loads(request.input_json) == {"item_name": "VR hour"}
        assert request.caller_phone_number is None

    @pytest.mark.parametrize("variant", ["missing", "wrong", "other_business", "no_id"])
    def test_unauthenticated_tool_calls_are_refused(self, variant: str) -> None:
        setup = build_voice_setup()
        other = BusinessId()
        headers: dict[str, str] = {
            "missing": {"X-Assistant-Business-Id": str(setup.business.id)},
            "wrong": {
                "X-Assistant-Business-Id": str(setup.business.id),
                "X-Assistant-Tool-Secret": "0" * 64,
            },
            "other_business": {
                "X-Assistant-Business-Id": str(setup.business.id),
                "X-Assistant-Tool-Secret": tool_secret(other),
            },
            "no_id": {"X-Assistant-Tool-Secret": tool_secret(setup.business.id)},
        }[variant]

        response = self.call_tool(
            setup, "get_price", {"arguments": {}, "conversation_id": "c"}, headers
        )

        assert response.status_code == 401
        assert setup.testbed.voice_tool_orchestrator.requests == []

    def test_unknown_tools_and_malformed_bodies(self) -> None:
        setup = build_voice_setup()

        unknown = self.call_tool(setup, "delete_everything", {"conversation_id": "c"})
        no_call = self.call_tool(setup, "get_price", {"arguments": {}})
        bad_arguments = self.call_tool(
            setup, "get_price", {"arguments": [1, 2], "conversation_id": "c"}
        )

        assert unknown.status_code == 404
        assert no_call.status_code == 422
        assert bad_arguments.status_code == 422

    def test_deleted_business_is_not_found(self) -> None:
        setup = build_voice_setup()
        ghost = BusinessId()

        response = self.call_tool(
            setup,
            "get_price",
            {"arguments": {}, "conversation_id": "c"},
            {
                "X-Assistant-Business-Id": str(ghost),
                "X-Assistant-Tool-Secret": tool_secret(ghost),
            },
        )

        assert response.status_code == 404

    def test_unconfigured_voice_webhooks_refuse_everything(self) -> None:
        setup = build_voice_setup(settings=build_settings(ELEVENLABS_WEBHOOK_SECRET=""))

        assert (
            self.call_tool(setup, "get_price", {"conversation_id": "c"}).status_code
            == 401
        )
