"""Builders the containers use for optional, settings-dependent providers."""

from pathlib import Path

import pytest

from app.clients.elevenlabs.elevenlabs_client import ElevenLabsClient
from app.clients.elevenlabs.unconfigured_elevenlabs_client import (
    UnconfiguredElevenLabsClient,
)
from app.clients.flitt.flitt_client import FlittClient
from app.clients.langfuse.langfuse_ingestion_client import LangfuseIngestionClient
from app.containers.factories import (
    DEFAULT_MENU_EXTRACTION_MODEL_ID,
    build_elevenlabs_client,
    build_flitt_client,
    build_langfuse_ingestion_client,
    build_llm_trace_facilitator,
    resolve_recordings_directory,
    select_menu_extraction_model_id,
)
from app.facilitators.observability.langfuse_trace_facilitator import (
    LangfuseTraceFacilitator,
)
from app.facilitators.observability.null_trace_facilitator import (
    NullTraceFacilitator,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.utilities.config_helpers.app_settings_assembler import assemble_app_settings


def test_voice_without_a_key_uses_a_stand_in_that_reports_it() -> None:
    client = build_elevenlabs_client(assemble_app_settings({}))

    assert isinstance(client, UnconfiguredElevenLabsClient)
    with pytest.raises(ExternalServiceError, match="ELEVENLABS_API_KEY"):
        client.create_agent({})
    with pytest.raises(ExternalServiceError, match="ELEVENLABS_API_KEY"):
        client.get_agent_tool_ids(VoiceAgentId("agent_1"))
    with pytest.raises(ExternalServiceError, match="ELEVENLABS_API_KEY"):
        client.delete_conversation(ProviderCallId("conv_1"))


def test_voice_with_a_key_uses_the_api_client() -> None:
    settings = assemble_app_settings({"ELEVENLABS_API_KEY": "xi-key"})

    assert isinstance(build_elevenlabs_client(settings), ElevenLabsClient)


def test_flitt_client_needs_both_merchant_settings() -> None:
    only_id = assemble_app_settings({"FLITT_MERCHANT_ID": "1549901"})
    both = assemble_app_settings(
        {"FLITT_MERCHANT_ID": "1549901", "FLITT_SECRET_KEY": "test"}
    )

    assert build_flitt_client(only_id) is None
    assert isinstance(build_flitt_client(both), FlittClient)


def test_quality_journal_is_langfuse_only_with_both_keys() -> None:
    without_keys = assemble_app_settings({"LANGFUSE_PUBLIC_KEY": "pk-lf-1"})
    with_keys = assemble_app_settings(
        {"LANGFUSE_PUBLIC_KEY": "pk-lf-1", "LANGFUSE_SECRET_KEY": "sk-lf-1"}
    )

    assert build_langfuse_ingestion_client(without_keys) is None
    client = build_langfuse_ingestion_client(with_keys)
    assert isinstance(client, LangfuseIngestionClient)
    assert isinstance(build_llm_trace_facilitator(None), NullTraceFacilitator)
    assert isinstance(build_llm_trace_facilitator(client), LangfuseTraceFacilitator)


@pytest.mark.parametrize(
    ("environment", "expected_model"),
    [
        ({}, "gpt-5-mini"),
        ({"LLM_MODEL_ID": "gpt-5"}, "gpt-5"),
        ({"LLM_PROVIDER": "anthropic"}, str(DEFAULT_MENU_EXTRACTION_MODEL_ID)),
        ({"LLM_PROVIDER": "scripted"}, str(DEFAULT_MENU_EXTRACTION_MODEL_ID)),
    ],
)
def test_menu_import_always_reads_with_an_openai_model(
    environment: dict[str, str],
    expected_model: str,
) -> None:
    settings = assemble_app_settings(environment)

    assert select_menu_extraction_model_id(settings) == expected_model


def test_recordings_directory_has_a_default_and_can_be_set() -> None:
    default = assemble_app_settings({})
    custom = assemble_app_settings({"RECORDINGS_DIRECTORY": "/srv/recordings"})

    assert resolve_recordings_directory(default) == Path("var/recordings")
    assert resolve_recordings_directory(custom) == Path("/srv/recordings")
