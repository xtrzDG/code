"""Read the model's menu lines; unusable lines are skipped and counted."""

import json
import re
from collections.abc import Collection
from typing import cast

from pydantic import ValidationError

from app.adapters.llm.menu_extraction.menu_extraction_prompt import MENU_ITEM_KINDS
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.dto.menu_import import ExtractedMenuItem, MenuExtraction
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.knowledge.constrained_integers import ServiceDurationMinutes
from app.schemas.typings.knowledge.constrained_strings import KnowledgeTag
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.menu_import.constrained_floats import ExtractionConfidence
from app.schemas.typings.menu_import.constrained_integers import MenuLineCount
from app.schemas.typings.menu_import.constrained_strings import ExtractedPriceAmount

MAX_TAGS_PER_ITEM: int = 5
PRICE_PATTERN: re.Pattern[str] = re.compile(r"^\d{1,12}(?:[.,]\d{1,4})?$")
CURRENCY_PATTERN: re.Pattern[str] = re.compile(r"^[A-Z]{3}$")
TAG_CLEANUP_PATTERN: re.Pattern[str] = re.compile(r"[^a-z0-9_\-]+")


def parse_menu_extraction(output_text: str) -> MenuExtraction:
    """
    Validate the model's JSON line by line.

    Raises:
        ExternalServiceError: the output is not the requested JSON object.
    """

    try:
        decoded: object = json.loads(output_text)
    except json.JSONDecodeError as error:
        raise ExternalServiceError("The menu model returned invalid JSON.") from error

    raw_items: object = (
        cast(dict[str, object], decoded).get("items")
        if isinstance(decoded, dict)
        else None
    )
    if not isinstance(raw_items, list):
        raise ExternalServiceError("The menu model returned no item list.")

    items: list[ExtractedMenuItem] = []
    skipped_line_count: int = 0
    for raw_item in cast(list[object], raw_items):
        item: ExtractedMenuItem | None = (
            read_menu_item(cast(dict[str, object], raw_item))
            if isinstance(raw_item, dict)
            else None
        )
        if item is None:
            skipped_line_count += 1
        else:
            items.append(item)

    return MenuExtraction(
        items=items,
        skipped_line_count=MenuLineCount(skipped_line_count),
    )


def read_menu_item(
    raw_item: dict[str, object],
    allowed_kinds: Collection[str] = MENU_ITEM_KINDS,
) -> ExtractedMenuItem | None:
    """One line, or None when its title is empty or its kind not allowed."""

    title: object = raw_item.get("title")
    kind: object = raw_item.get("kind")
    if (
        not isinstance(title, str)
        or title.strip() == ""
        or not isinstance(kind, str)
        or kind not in allowed_kinds
    ):
        return None

    body: object = raw_item.get("body")
    try:
        return ExtractedMenuItem(
            kind=KnowledgeItemKind(kind),
            title=KnowledgeTitle(title.strip()),
            body=(
                KnowledgeBody(body.strip())
                if isinstance(body, str) and body.strip() != ""
                else None
            ),
            price=read_price(raw_item.get("price")),
            currency_code=read_currency(raw_item.get("currency")),
            duration_minutes=read_duration(raw_item.get("duration_minutes")),
            tags=read_tags(raw_item.get("tags")),
            confidence=read_confidence(raw_item.get("confidence")),
        )
    except ValidationError, ValueError:
        return None


def read_price(raw_price: object) -> ExtractedPriceAmount | None:
    if isinstance(raw_price, int | float) and not isinstance(raw_price, bool):
        raw_price = f"{raw_price}"

    if not isinstance(raw_price, str):
        return None

    compact: str = raw_price.strip().replace(" ", "").replace(" ", "")
    if PRICE_PATTERN.fullmatch(compact) is None:
        return None

    return ExtractedPriceAmount(compact.replace(",", "."))


def read_currency(raw_currency: object) -> CurrencyCode | None:
    if not isinstance(raw_currency, str):
        return None

    code: str = raw_currency.strip().upper()
    return CurrencyCode(code) if CURRENCY_PATTERN.fullmatch(code) else None


def read_duration(raw_duration: object) -> ServiceDurationMinutes | None:
    if not isinstance(raw_duration, int) or isinstance(raw_duration, bool):
        return None

    try:
        return ServiceDurationMinutes(raw_duration)
    except ValueError:
        return None


def read_tags(raw_tags: object) -> list[KnowledgeTag]:
    if not isinstance(raw_tags, list):
        return []

    tags: list[KnowledgeTag] = []
    for raw_tag in cast(list[object], raw_tags):
        if not isinstance(raw_tag, str):
            continue

        cleaned: str = TAG_CLEANUP_PATTERN.sub("-", raw_tag.strip().lower()).strip("-_")
        try:
            tag = KnowledgeTag(cleaned)
        except ValueError:
            continue

        if tag not in tags:
            tags.append(tag)

    return tags[:MAX_TAGS_PER_ITEM]


def read_confidence(raw_confidence: object) -> ExtractionConfidence:
    if isinstance(raw_confidence, bool) or not isinstance(raw_confidence, int | float):
        return ExtractionConfidence(0.0)

    return ExtractionConfidence(min(1.0, max(0.0, float(raw_confidence))))
