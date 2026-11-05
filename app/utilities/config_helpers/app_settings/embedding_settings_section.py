"""EMBEDDINGS_API_KEY and EMBEDDINGS_MODEL_ID: the hybrid knowledge search."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.embedding_settings import (
    DEFAULT_EMBEDDINGS_MODEL_ID,
    EmbeddingSettings,
)
from app.schemas.typings.knowledge.constrained_strings import EmbeddingModelId
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
    parse_setting,
    read_text,
)


class EmbeddingSettingsSection(TypedDict):
    """The `AppSettings` field of the knowledge embeddings."""

    embeddings: EmbeddingSettings


def read_embedding_settings(
    environment_variables: Mapping[str, str],
) -> EmbeddingSettingsSection:
    """No key, no embeddings: the knowledge search stays lexical."""

    return EmbeddingSettingsSection(
        embeddings=EmbeddingSettings(
            api_key=optional_text(
                environment_variables, "EMBEDDINGS_API_KEY", PlatformSecret
            ),
            model_id=parse_setting(
                "EMBEDDINGS_MODEL_ID",
                read_text(
                    environment_variables,
                    "EMBEDDINGS_MODEL_ID",
                    DEFAULT_EMBEDDINGS_MODEL_ID,
                ),
                EmbeddingModelId,
            ),
        )
    )
