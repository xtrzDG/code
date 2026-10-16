"""Small owner text catalogs written to a temporary directory."""

import json
from pathlib import Path

from app.schemas.constants.localization import CABINET_LANGUAGES, TextReviewStatus

ENGLISH_TEXTS: dict[str, str] = {
    "plans.chat.name": "Chat",
    "billing.notice": "{business}: pay {amount}.",
    "niches.cafe.handoff_rules.1": "Complaint",
    "niches.cafe.handoff_rules.2": "Large group",
}


def write_catalog_file(
    directory: Path,
    language: str,
    texts: dict[str, str],
    *,
    review_status: TextReviewStatus = TextReviewStatus.REVIEWED,
    draft_keys: list[str] | None = None,
    declared_language: str | None = None,
) -> None:
    payload = {
        "language": declared_language if declared_language is not None else language,
        "review_status": review_status.value,
        "draft_keys": draft_keys if draft_keys is not None else [],
        "texts": texts,
    }
    (directory / f"{language}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def write_catalog(
    directory: Path,
    texts_by_language: dict[str, dict[str, str]] | None = None,
) -> Path:
    """English plus every other cabinet language (copies of English unless given)."""

    given: dict[str, dict[str, str]] = texts_by_language or {}
    for language in CABINET_LANGUAGES:
        texts: dict[str, str] = given.get(language.value, dict(ENGLISH_TEXTS))
        status: TextReviewStatus = (
            TextReviewStatus.NEEDS_REVIEW
            if language.value in {"he", "de"}
            else TextReviewStatus.REVIEWED
        )
        write_catalog_file(directory, language.value, texts, review_status=status)

    return directory
