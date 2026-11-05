"""
The DPA texts are built into the image: a DPA_DOCUMENT_VERSION deployed onto
a build without its text is refused at startup in production, so no owner
is asked to accept a version nobody can read.
"""

import logging
from collections.abc import Mapping
from pathlib import Path

import pytest

from app.containers.app import AppContainer
from app.main import check_dpa_document
from app.registries.legal.legal_document_registry import LegalDocumentRegistry
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.e2e.workshop_container import replace_provider

PRODUCTION: dict[str, str] = {"APP_ENV": "production", "ENCRYPTION_KEY": "x" * 32}


def container_with(
    environment: Mapping[str, str],
    legal_documents: Path | None = None,
) -> AppContainer:
    container = AppContainer()
    replace_provider(container.config.app_settings, assemble_app_settings(environment))
    if legal_documents is not None:
        replace_provider(
            container.registries.legal_document_registry,
            LegalDocumentRegistry(legal_documents),
        )
    return container


def test_the_default_version_has_its_text_in_the_repository() -> None:
    check_dpa_document(container_with({}))
    check_dpa_document(container_with(PRODUCTION))


def test_production_refuses_a_version_whose_text_is_not_in_the_build(
    tmp_path: Path,
) -> None:
    (tmp_path / "dpa-2026-10-01.en.md").write_text("# DPA\n", encoding="utf-8")

    with pytest.raises(ValidationFailedError, match="2027-01-01"):
        check_dpa_document(
            container_with(
                {**PRODUCTION, "DPA_DOCUMENT_VERSION": "2027-01-01"},
                tmp_path,
            )
        )


def test_development_only_warns(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.main"):
        check_dpa_document(
            container_with({"DPA_DOCUMENT_VERSION": "2027-01-01"}, tmp_path)
        )

    assert "dpa-2027-01-01" in caplog.text
