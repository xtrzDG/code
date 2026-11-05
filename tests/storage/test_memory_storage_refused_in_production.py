"""
Production never serves from in-memory collections (each instance would
see only its own data, lose it on restart and still report /readyz ready):
the startup check refuses DATABASE_URL missing first, and the storage
factory refuses an in-memory collection there as well.
"""

import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.storage.postgres.document_collection_factory import (
    build_document_collection,
)
from app.main import build_application
from app.schemas.domain.users import UserDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.platform.production_settings import container_with, production_with


def test_production_without_a_database_builds_no_collection() -> None:
    settings = assemble_app_settings(
        {"APP_ENV": "production", "ENCRYPTION_KEY": "x" * 32}
    )

    with pytest.raises(ValidationFailedError, match="DATABASE_URL is not set"):
        build_document_collection(UserDocument, "users", settings)


@pytest.mark.parametrize("environment", ["development", "test"])
def test_development_and_tests_keep_their_memory(environment: str) -> None:
    settings = assemble_app_settings({"APP_ENV": environment})

    collection = build_document_collection(UserDocument, "users", settings)

    assert isinstance(collection, InMemoryDocumentCollectionAdapter)


def test_production_on_memory_storage_never_serves_a_readiness_probe() -> None:
    # Even past the startup checks (a test client without its lifespan),
    # the API's routes cannot be built on in-memory collections, so GET
    # /readyz never answers "ready" there.
    without_database = production_with(
        {
            "DATABASE_URL": None,
            "DATABASE_URL_TENANT": None,
            "DATABASE_URL_PLATFORM": None,
        }
    )

    with pytest.raises(ValidationFailedError, match="DATABASE_URL is not set"):
        build_application(container_with(without_database))
