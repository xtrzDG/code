"""
The owner text catalog: the owner-facing texts of plans, niche templates,
staff notifications, call forwarding guides and billing, one JSON file per
cabinet language (`app/registries/localization/texts/<language>.json`).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.localization import CabinetLanguage, TextReviewStatus
from app.schemas.typings.localization.constrained_strings import OwnerTextKey
from app.schemas.typings.localization.strings import LocalizedTextValue


class TextCatalogFile(ImmutableDTO):
    """
    One language of the catalog.

    English is the source: every other file holds a subset of its keys. A
    file of drafts is NEEDS_REVIEW as a whole; in a reviewed file,
    `draft_keys` names single texts that were drafted later and still wait
    for a native speaker. Text values are `str.format` templates whose
    `{placeholders}` match the English text of the same key.
    """

    language: CabinetLanguage
    review_status: TextReviewStatus
    draft_keys: list[OwnerTextKey] = Field(default_factory=list[OwnerTextKey])
    texts: dict[OwnerTextKey, LocalizedTextValue]


class TextCatalog(ImmutableDTO):
    """Every cabinet language of the catalog, as read and checked at startup."""

    files: dict[CabinetLanguage, TextCatalogFile]
