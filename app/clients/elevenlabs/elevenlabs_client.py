import httpx

from app.contracts.channel_clients import ElevenLabsApiClientContract, JsonObject
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.channels.strings import VoicePlatformToolId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.json_values import (
    parse_json_object,
    read_identifier,
    read_object,
    read_strings,
    read_text,
)

API_KEY_HEADER: str = "xi-api-key"
REQUEST_TIMEOUT_SECONDS: float = 20.0
NOT_FOUND_STATUS_CODE: int = 404
ASSISTANT_TOOL_NAMES: frozenset[str] = frozenset(
    tool_name.value for tool_name in AssistantToolName
)


class ElevenLabsClient(ElevenLabsApiClientContract):
    """
    Minimal ElevenLabs Agents API client (header `xi-api-key`).

    Agents: POST /v1/convai/agents/create, GET and PATCH
    /v1/convai/agents/{agent_id}. Tools: POST /v1/convai/tools, GET, PATCH and
    DELETE /v1/convai/tools/{tool_id}. Conversations: DELETE
    /v1/convai/conversations/{conversation_id}. The base URL selects the data
    residency (https://api.eu.residency.elevenlabs.io keeps data in the EU).
    """

    def __init__(
        self,
        api_key: PlatformSecret,
        base_url: PublicBaseUrl,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http_client: httpx.Client = httpx.Client(
            base_url=str(base_url).rstrip("/"),
            headers={API_KEY_HEADER: str(api_key)},
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )

    def create_agent(self, agent_config: JsonObject) -> VoiceAgentId:
        body: JsonObject = self._send("POST", "/v1/convai/agents/create", agent_config)
        agent_id: str | None = read_text(body, "agent_id")
        if agent_id is None:
            raise ExternalServiceError("ElevenLabs created an agent without an id.")

        return VoiceAgentId(agent_id)

    def get_agent_tool_ids(
        self,
        agent_id: VoiceAgentId,
    ) -> list[VoicePlatformToolId] | None:
        body: JsonObject | None = self._read(f"/v1/convai/agents/{agent_id}")
        if body is None:
            return None

        conversation_config: JsonObject = read_object(body, "conversation_config") or {}
        agent: JsonObject = read_object(conversation_config, "agent") or {}
        prompt: JsonObject = read_object(agent, "prompt") or {}
        return [
            VoicePlatformToolId(tool_id) for tool_id in read_strings(prompt, "tool_ids")
        ]

    def update_agent(self, agent_id: VoiceAgentId, agent_config: JsonObject) -> None:
        self._send("PATCH", f"/v1/convai/agents/{agent_id}", agent_config)

    def create_tool(self, tool_config: JsonObject) -> VoicePlatformToolId:
        body: JsonObject = self._send(
            "POST",
            "/v1/convai/tools",
            {"tool_config": tool_config},
        )
        tool_id: str | None = read_identifier(body, "id")
        if tool_id is None:
            raise ExternalServiceError("ElevenLabs created a tool without an id.")

        return VoicePlatformToolId(tool_id)

    def get_tool_name(self, tool_id: VoicePlatformToolId) -> AssistantToolName | None:
        body: JsonObject | None = self._read(f"/v1/convai/tools/{tool_id}")
        if body is None:
            return None

        tool_config: JsonObject = read_object(body, "tool_config") or {}
        tool_name: str | None = read_text(tool_config, "name")
        if tool_name is None or tool_name not in ASSISTANT_TOOL_NAMES:
            return None

        return AssistantToolName(tool_name)

    def update_tool(
        self, tool_id: VoicePlatformToolId, tool_config: JsonObject
    ) -> None:
        self._send("PATCH", f"/v1/convai/tools/{tool_id}", {"tool_config": tool_config})

    def delete_tool(self, tool_id: VoicePlatformToolId) -> None:
        self._delete(f"/v1/convai/tools/{tool_id}")

    def delete_conversation(self, conversation_id: ProviderCallId) -> None:
        self._delete(f"/v1/convai/conversations/{conversation_id}")

    def _read(self, path: str) -> JsonObject | None:
        response: httpx.Response = self._perform("GET", path, None)
        if response.status_code == NOT_FOUND_STATUS_CODE:
            return None

        return self._parse(response, path)

    def _send(self, method: str, path: str, payload: JsonObject) -> JsonObject:
        return self._parse(self._perform(method, path, payload), path)

    def _delete(self, path: str) -> None:
        response: httpx.Response = self._perform("DELETE", path, None)
        if response.status_code != NOT_FOUND_STATUS_CODE:
            self._parse(response, path)

    def _perform(
        self,
        method: str,
        path: str,
        payload: JsonObject | None,
    ) -> httpx.Response:
        try:
            return self._http_client.request(method, path, json=payload)
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"ElevenLabs request failed: {type(error).__name__}."
            ) from None

    def _parse(self, response: httpx.Response, path: str) -> JsonObject:
        body: JsonObject = parse_json_object(response.content) or {}
        if response.status_code < 400:
            return body

        detail: object = body.get("detail")
        detail_text: str = detail if isinstance(detail, str) else ""
        detail_object: JsonObject | None = read_object(body, "detail")
        if detail_object is not None:
            detail_text = read_text(detail_object, "message") or ""

        raise ExternalServiceError(
            f"ElevenLabs {path.split('/')[3]} request returned HTTP "
            f"{response.status_code}{': ' + detail_text if detail_text else ''}."
        )
