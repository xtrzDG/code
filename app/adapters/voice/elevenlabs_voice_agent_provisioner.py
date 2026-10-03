"""Create, update and remove the ElevenLabs voice agent of a business."""

import logging

from app.adapters.voice.elevenlabs_agent_config import build_agent_config
from app.adapters.voice.elevenlabs_tool_config import build_tool_config
from app.contracts.channel_clients import ElevenLabsApiClientContract, JsonObject
from app.contracts.voice_platform import VoiceAgentProvisionerAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.voice import VoiceAgentSpec
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.constrained_strings import VoiceToolSecret
from app.schemas.typings.channels.strings import VoicePlatformToolId
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.channel_endpoints import (
    VOICE_BUSINESS_ID_HEADER,
    VOICE_TOOL_SECRET_HEADER,
)
from app.utilities.channels.webhook_signatures import derive_voice_tool_secret

logger: logging.Logger = logging.getLogger(__name__)


class ElevenLabsVoiceAgentProvisioner(VoiceAgentProvisionerAdapterContract):
    """
    One ElevenLabs agent per business, assembled from the same version as
    the chat (concept sections 4 and 7).

    - Prompt: the version's instruction; first message: the greeting in the
      business's default language, other languages as language presets with
      their own greetings and the language detection system tool.
    - Tools: one webhook tool per assistant tool, POST
      APP_BASE_URL/v1/voice/tools/{tool}, with the model's arguments under
      "arguments" and the call id and caller id filled by ElevenLabs. Every
      request carries the business id and the business's tool secret
      (derived from ELEVENLABS_WEBHOOK_SECRET) in headers.
    - Call start: the conversation-initiation webhook may refresh the
      greeting for each call.

    Updating keeps the agent id: tools are updated in place by name, new
    ones created, and tools the version no longer uses deleted afterwards.
    """

    def __init__(
        self,
        elevenlabs_client: ElevenLabsApiClientContract,
        app_settings: AppSettings,
    ) -> None:
        self._elevenlabs_client: ElevenLabsApiClientContract = elevenlabs_client
        self._app_settings: AppSettings = app_settings

    def list_missing_settings(self) -> list[EnvironmentVariableName]:
        """ELEVENLABS_API_KEY and ELEVENLABS_WEBHOOK_SECRET, when not set."""

        missing: list[EnvironmentVariableName] = []
        if self._app_settings.elevenlabs_api_key is None:
            missing.append(EnvironmentVariableName("ELEVENLABS_API_KEY"))

        if self._app_settings.elevenlabs_webhook_secret is None:
            missing.append(EnvironmentVariableName("ELEVENLABS_WEBHOOK_SECRET"))

        return missing

    def upsert_agent(self, spec: VoiceAgentSpec) -> VoiceAgentId:
        webhook_secret: PlatformSecret | None = (
            self._app_settings.elevenlabs_webhook_secret
        )
        if webhook_secret is None:
            raise ExternalServiceError(
                "The voice agent cannot be set up: ELEVENLABS_WEBHOOK_SECRET "
                "is not configured."
            )

        tool_secret: VoiceToolSecret = derive_voice_tool_secret(
            webhook_secret,
            spec.business_id,
        )
        request_headers: JsonObject = {
            VOICE_BUSINESS_ID_HEADER: str(spec.business_id),
            VOICE_TOOL_SECRET_HEADER: str(tool_secret),
        }
        tool_configs: list[JsonObject] = [
            build_tool_config(tool, str(spec.tool_webhook_base_url), request_headers)
            for tool in spec.tools
        ]

        existing_tool_ids: list[VoicePlatformToolId] | None = None
        if spec.existing_agent_id is not None:
            existing_tool_ids = self._elevenlabs_client.get_agent_tool_ids(
                spec.existing_agent_id
            )

        if spec.existing_agent_id is None or existing_tool_ids is None:
            return self._create_agent(spec, tool_configs, request_headers)

        kept_tool_ids, stale_tool_ids = self._synchronize_tools(
            existing_tool_ids,
            tool_configs,
        )
        self._elevenlabs_client.update_agent(
            spec.existing_agent_id,
            build_agent_config(spec, kept_tool_ids, request_headers),
        )
        self._delete_tools(stale_tool_ids)
        return spec.existing_agent_id

    def remove_agent(self, agent_id: VoiceAgentId) -> None:
        tool_ids: list[VoicePlatformToolId] = (
            self._elevenlabs_client.get_agent_tool_ids(agent_id) or []
        )
        self._elevenlabs_client.delete_agent(agent_id)
        self._delete_tools(tool_ids)

    def _create_agent(
        self,
        spec: VoiceAgentSpec,
        tool_configs: list[JsonObject],
        request_headers: JsonObject,
    ) -> VoiceAgentId:
        tool_ids: list[VoicePlatformToolId] = []
        try:
            for tool_config in tool_configs:
                tool_ids.append(self._elevenlabs_client.create_tool(tool_config))

            return self._elevenlabs_client.create_agent(
                build_agent_config(spec, tool_ids, request_headers)
            )
        except ApplicationError:
            self._delete_tools(tool_ids)
            raise

    def _synchronize_tools(
        self,
        existing_tool_ids: list[VoicePlatformToolId],
        tool_configs: list[JsonObject],
    ) -> tuple[list[VoicePlatformToolId], list[VoicePlatformToolId]]:
        """Tool ids for the agent, and tools to delete once it no longer uses them."""

        existing_by_name: dict[str, VoicePlatformToolId] = {}
        stale_tool_ids: list[VoicePlatformToolId] = []
        for tool_id in existing_tool_ids:
            tool_name: AssistantToolName | None = self._elevenlabs_client.get_tool_name(
                tool_id
            )
            if tool_name is None:
                continue

            if tool_name.value in existing_by_name:
                stale_tool_ids.append(tool_id)
            else:
                existing_by_name[tool_name.value] = tool_id

        kept_tool_ids: list[VoicePlatformToolId] = []
        for tool_config in tool_configs:
            existing_tool_id: VoicePlatformToolId | None = existing_by_name.pop(
                str(tool_config["name"]),
                None,
            )
            if existing_tool_id is None:
                kept_tool_ids.append(self._elevenlabs_client.create_tool(tool_config))
            else:
                self._elevenlabs_client.update_tool(existing_tool_id, tool_config)
                kept_tool_ids.append(existing_tool_id)

        stale_tool_ids.extend(existing_by_name.values())
        return kept_tool_ids, stale_tool_ids

    def _delete_tools(self, tool_ids: list[VoicePlatformToolId]) -> None:
        for tool_id in tool_ids:
            try:
                self._elevenlabs_client.delete_tool(tool_id)
            except ApplicationError as error:
                logger.warning(
                    "Unused voice tool %s was not deleted: %s", tool_id, error
                )
