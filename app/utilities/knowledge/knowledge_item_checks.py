"""Rules for the values of a knowledge item.

- the kind must be one the niche uses (FAQ and policies everywhere);
- prices are integers in minor units of the business currency, and a price
  in another currency is rejected;
- texts are checked (not blank, limited length) and stored as written,
  tags and languages de-duplicated, attribute keys unique.
"""

from collections.abc import Sequence

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeAttribute
from app.schemas.dto.niches import NicheTemplate
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.knowledge.constrained_strings import KnowledgeTag
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)

MAX_TITLE_LENGTH: int = 300
MAX_BODY_LENGTH: int = 8000
MAX_TAGS: int = 30
MAX_ATTRIBUTES: int = 30
MAX_ATTRIBUTE_VALUE_LENGTH: int = 500
ALWAYS_ALLOWED_KINDS: frozenset[KnowledgeItemKind] = frozenset(
    {KnowledgeItemKind.FAQ, KnowledgeItemKind.POLICY}
)


def check_kind(template: NicheTemplate, kind: KnowledgeItemKind) -> KnowledgeItemKind:
    if kind in ALWAYS_ALLOWED_KINDS or kind in template.knowledge_kinds:
        return kind

    allowed: list[str] = sorted(
        {*template.knowledge_kinds, *ALWAYS_ALLOWED_KINDS},
    )
    raise ValidationFailedError(
        f"Niche {template.key} does not use {kind} items; use one of "
        f"{', '.join(allowed)}."
    )


def check_price(
    business: BusinessDocument,
    price_minor: MoneyAmountMinor | None,
    currency_code: CurrencyCode | None,
) -> tuple[MoneyAmountMinor | None, CurrencyCode | None]:
    """The price and the business currency, or (None, None) without a price."""

    if currency_code is not None and currency_code != business.currency_code:
        raise ValidationFailedError(
            f"Prices must be in the business currency {business.currency_code}, "
            f"not {currency_code}."
        )

    if price_minor is None:
        return None, None

    return price_minor, business.currency_code


def check_title(title: KnowledgeTitle) -> KnowledgeTitle:
    """The title as written; blank or overly long titles are rejected."""

    stripped_length: int = len(title.strip())
    if stripped_length == 0:
        raise ValidationFailedError("A knowledge item needs a title.")

    if stripped_length > MAX_TITLE_LENGTH:
        raise ValidationFailedError(
            f"A title must be at most {MAX_TITLE_LENGTH} characters."
        )

    return title


def check_body(body: KnowledgeBody | None) -> KnowledgeBody | None:
    """The text as written, or None when it is missing or blank."""

    if body is None or body.strip() == "":
        return None

    if len(body.strip()) > MAX_BODY_LENGTH:
        raise ValidationFailedError(
            f"A text must be at most {MAX_BODY_LENGTH} characters."
        )

    return body


def unique_tags(tags: Sequence[KnowledgeTag]) -> list[KnowledgeTag]:
    """Tags without repeats, in their first order."""

    kept: list[KnowledgeTag] = list(dict.fromkeys(tags))
    if len(kept) > MAX_TAGS:
        raise ValidationFailedError(f"An item may have at most {MAX_TAGS} tags.")

    return kept


def check_attributes(
    attributes: Sequence[KnowledgeAttribute],
) -> list[KnowledgeAttribute]:
    """Attributes with unique keys and non-blank values of limited length."""

    if len(attributes) > MAX_ATTRIBUTES:
        raise ValidationFailedError(
            f"An item may have at most {MAX_ATTRIBUTES} attributes."
        )

    seen_keys: set[str] = set()
    for attribute in attributes:
        if attribute.key in seen_keys:
            raise ValidationFailedError(f"Attribute {attribute.key} is repeated.")

        seen_keys.add(attribute.key)
        value_length: int = len(attribute.value.strip())
        if value_length == 0 or value_length > MAX_ATTRIBUTE_VALUE_LENGTH:
            raise ValidationFailedError(
                f"Attribute {attribute.key} needs a value of 1 to "
                f"{MAX_ATTRIBUTE_VALUE_LENGTH} characters."
            )

    return [attribute.model_copy() for attribute in attributes]


def unique_languages(languages: Sequence[LanguageTag]) -> list[LanguageTag]:
    return list(dict.fromkeys(languages))
