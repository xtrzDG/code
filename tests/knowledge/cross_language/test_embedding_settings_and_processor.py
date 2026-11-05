"""
EMBEDDINGS_API_KEY turns the hybrid search on; it is a new flow of personal
data to OpenAI's EU project, so it is covered only once its 30-day notice to
owners has run.
"""

from datetime import date

import pytest

from app.registries.legal.processor_use_catalog import PROCESSOR_USES
from app.registries.legal.subprocessor_catalog import SUBPROCESSORS
from app.schemas.constants.legal import ProcessorFlow
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.legal.processor_coverage import (
    configure_uses,
    configured_client_module,
    find_uncovered_uses,
)

BASE_ENVIRONMENT: dict[str, str] = {
    "APP_ENV": "development",
    "LLM_PROVIDER": "scripted",
}


def test_without_a_key_the_search_stays_lexical_and_reaches_nobody() -> None:
    settings = assemble_app_settings(BASE_ENVIRONMENT)

    assert settings.embeddings.api_key is None
    assert str(settings.embeddings.model_id) == "text-embedding-3-small"
    assert (
        configured_client_module(ProcessorFlow.KNOWLEDGE_EMBEDDINGS, settings) is None
    )


def test_the_key_and_model_are_read_and_a_bad_model_names_its_variable() -> None:
    settings = assemble_app_settings(
        {
            **BASE_ENVIRONMENT,
            "EMBEDDINGS_API_KEY": "test-token-0000",
            "EMBEDDINGS_MODEL_ID": "text-embedding-3-large",
        }
    )

    assert str(settings.embeddings.api_key) == "test-token-0000"
    assert str(settings.embeddings.model_id) == "text-embedding-3-large"
    assert (
        str(configured_client_module(ProcessorFlow.KNOWLEDGE_EMBEDDINGS, settings))
        == "openai"
    )
    with pytest.raises(ValidationFailedError, match="EMBEDDINGS_MODEL_ID"):
        assemble_app_settings({**BASE_ENVIRONMENT, "EMBEDDINGS_MODEL_ID": "a b"})


@pytest.mark.parametrize(
    ("day", "is_covered"),
    [(date(2026, 11, 21), False), (date(2026, 11, 22), True)],
)
def test_the_embeddings_flow_is_covered_once_its_notice_has_run(
    day: date, is_covered: bool
) -> None:
    settings = assemble_app_settings(
        {**BASE_ENVIRONMENT, "EMBEDDINGS_API_KEY": "test-token-0000"}
    )

    uncovered = find_uncovered_uses(
        configure_uses(list(PROCESSOR_USES), settings), list(SUBPROCESSORS), day
    )

    assert (
        ProcessorFlow.KNOWLEDGE_EMBEDDINGS not in [item.flow for item in uncovered]
    ) is is_covered
