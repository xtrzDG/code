"""The catalog files are read once and refused when they disagree with English."""

from pathlib import Path

import pytest

from app.schemas.constants.localization import CabinetLanguage, TextReviewStatus
from app.utilities.localization.owner_texts import OWNER_TEXTS_DIRECTORY
from app.utilities.localization.text_catalog_files import (
    TextCatalogError,
    read_text_catalog,
)
from tests.localization.text_catalog.catalog_builders import (
    ENGLISH_TEXTS,
    write_catalog,
    write_catalog_file,
)


def test_the_shipped_catalog_reads_in_every_cabinet_language() -> None:
    catalog = read_text_catalog(OWNER_TEXTS_DIRECTORY)

    assert set(catalog.files) == set(CabinetLanguage)
    assert catalog.files[CabinetLanguage.ENGLISH].review_status is (
        TextReviewStatus.REVIEWED
    )


def test_a_consistent_catalog_keeps_every_file(tmp_path: Path) -> None:
    catalog = read_text_catalog(write_catalog(tmp_path))

    assert list(catalog.files[CabinetLanguage.ITALIAN].texts) == list(ENGLISH_TEXTS)
    assert catalog.files[CabinetLanguage.ITALIAN].review_status is (
        TextReviewStatus.NEEDS_REVIEW
    )


def test_a_missing_language_file_stops_the_start(tmp_path: Path) -> None:
    write_catalog(tmp_path)
    (tmp_path / "it.json").unlink()

    with pytest.raises(TextCatalogError, match="it.json cannot be read"):
        read_text_catalog(tmp_path)


def test_a_malformed_file_stops_the_start(tmp_path: Path) -> None:
    write_catalog(tmp_path)
    (tmp_path / "it.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(TextCatalogError, match="it.json cannot be read"):
        read_text_catalog(tmp_path)


def test_a_file_holding_another_language_is_refused(tmp_path: Path) -> None:
    write_catalog(tmp_path)
    write_catalog_file(tmp_path, "it", dict(ENGLISH_TEXTS), declared_language="en")

    with pytest.raises(TextCatalogError, match="it.json holds the texts of en"):
        read_text_catalog(tmp_path)


def test_english_must_be_the_reviewed_source(tmp_path: Path) -> None:
    write_catalog(tmp_path)
    write_catalog_file(
        tmp_path,
        "en",
        dict(ENGLISH_TEXTS),
        review_status=TextReviewStatus.NEEDS_REVIEW,
    )

    with pytest.raises(TextCatalogError, match="en.json is the source"):
        read_text_catalog(tmp_path)


def test_a_translation_key_english_lacks_is_refused(tmp_path: Path) -> None:
    write_catalog(tmp_path, {"it": {**ENGLISH_TEXTS, "plans.gone.name": "Vecchio"}})

    with pytest.raises(TextCatalogError, match="it.json has keys en.json lacks"):
        read_text_catalog(tmp_path)


def test_a_draft_key_must_name_a_text_of_its_file(tmp_path: Path) -> None:
    write_catalog(tmp_path)
    write_catalog_file(
        tmp_path,
        "it",
        {"plans.chat.name": "Chat"},
        draft_keys=["billing.notice"],
    )

    with pytest.raises(TextCatalogError, match="it.json names drafts it lacks"):
        read_text_catalog(tmp_path)


@pytest.mark.parametrize(
    "translation",
    ["{business}: paga.", "{business}: paga {amount} {extra}."],
)
def test_translations_keep_the_english_placeholders(
    tmp_path: Path, translation: str
) -> None:
    write_catalog(tmp_path, {"it": {**ENGLISH_TEXTS, "billing.notice": translation}})

    with pytest.raises(TextCatalogError, match="it.json billing.notice"):
        read_text_catalog(tmp_path)


def test_a_missing_translation_is_allowed_and_reads_english(tmp_path: Path) -> None:
    write_catalog(tmp_path, {"it": {"plans.chat.name": "Chat"}})

    catalog = read_text_catalog(tmp_path)

    assert list(catalog.files[CabinetLanguage.ITALIAN].texts) == ["plans.chat.name"]
