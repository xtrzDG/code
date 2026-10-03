"""
Every environment variable is documented where people look for it, and every
documented one is read by something (sources in environment_sources.py).
"""

import inspect
from collections.abc import Iterator, Mapping

import anthropic
import openai
import pytest

from app.clients.anthropic import anthropic_messages_client
from app.clients.openai import openai_responses_client
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.config_helpers.app_settings.llm_settings_section import (
    DEFAULT_OPENAI_BASE_URL,
)
from tests.platform.deployment_variables import (
    COMPOSE_VARIABLES,
    DEPLOYMENT_VARIABLES,
    REQUIRED_CABINET_VARIABLES,
)
from tests.platform.environment_sources import (
    assembler_variables,
    backend_variables,
    cabinet_variables,
    env_file_values,
    table_variables,
)

# The assembler reads some variables only in some environments: each
# scenario is assembled once and every name it asks for is recorded.
ASSEMBLY_SCENARIOS: tuple[dict[str, str], ...] = (
    {},
    {
        "APP_ENV": "production",
        "ELEVENLABS_API_BASE_URL": "https://api.elevenlabs.io",
        "ELEVENLABS_ALLOW_NON_EU_REGION": "true",
    },
)


class RecordingEnvironment(Mapping[str, str]):
    """An environment that remembers which variables were asked for."""

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values: dict[str, str] = dict(values)
        self.read_names: set[str] = set()

    def __getitem__(self, key: str) -> str:
        # Mapping.get and `in` ask here too.
        self.read_names.add(key)
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        raise AssertionError("The settings assembler must read variables by name.")

    def __len__(self) -> int:
        return len(self._values)


def test_the_name_scan_finds_exactly_what_the_assembler_reads() -> None:
    # The other tests scan the assembler's source; assembling real settings
    # proves that the scan misses nothing and lists nothing unread.
    read_names: set[str] = set()
    for scenario in ASSEMBLY_SCENARIOS:
        environment = RecordingEnvironment(scenario)
        assemble_app_settings(environment)
        read_names |= environment.read_names

    assert read_names == assembler_variables()


def test_every_backend_variable_is_in_env_example() -> None:
    documented: set[str] = set(env_file_values(".env.example", False))

    assert backend_variables() - documented == set()


def test_every_env_example_variable_is_read() -> None:
    documented: set[str] = set(env_file_values(".env.example", False))

    unread: set[str] = (
        documented - backend_variables() - DEPLOYMENT_VARIABLES - COMPOSE_VARIABLES
    )

    assert unread == set()


def test_the_readme_environment_table_lists_every_backend_variable() -> None:
    table: set[str] = table_variables("README.md", "## Окружение")
    expected: set[str] = backend_variables() | DEPLOYMENT_VARIABLES

    assert expected - table == set()
    assert table - expected == set()


def test_the_sdks_read_their_keys_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-the-environment")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-the-environment")

    openai_client = openai.OpenAI(base_url=DEFAULT_OPENAI_BASE_URL)
    anthropic_client = anthropic.Anthropic()

    assert openai_client.api_key == "sk-from-the-environment"
    assert anthropic_client.api_key == "sk-ant-from-the-environment"
    for client_module in (openai_responses_client, anthropic_messages_client):
        assert "api_key=" not in inspect.getsource(client_module)


def test_every_cabinet_variable_is_documented() -> None:
    read_names: set[str] = cabinet_variables()

    assert read_names >= REQUIRED_CABINET_VARIABLES
    assert set(env_file_values("web/.env.example", True)) == read_names
    assert table_variables("web/README.md", "### Environment") == read_names
