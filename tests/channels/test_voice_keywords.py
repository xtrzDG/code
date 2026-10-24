"""What the voice agent's speech recognition listens for."""

from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.knowledge import KnowledgeAliasStatus, KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeAlias, KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.bookings.constrained_integers import ResourceCapacity
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAliasText
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.voice_keywords import (
    MAX_ASR_KEYWORDS,
    MAX_KEYWORD_ITEMS,
    collect_asr_keywords,
)

BUSINESS_ID = BusinessId()
NAME = BusinessName("Café Rustaveli")
LANGUAGES = [LanguageTag("ka"), LanguageTag("ru"), LanguageTag("en")]


def item(
    title: str,
    kind: KnowledgeItemKind = KnowledgeItemKind.MENU_ITEM,
    aliases: tuple[tuple[str, str, KnowledgeAliasStatus], ...] = (),
    is_active: bool = True,
) -> KnowledgeItemDocument:
    return KnowledgeItemDocument(
        business_id=BUSINESS_ID,
        kind=kind,
        title=KnowledgeTitle(title),
        is_active=is_active,
        aliases=[
            KnowledgeAlias(
                language=LanguageTag(language),
                text=KnowledgeAliasText(text),
                status=status,
            )
            for language, text, status in aliases
        ],
    )


def resource(name: str, is_active: bool = True) -> ResourceDocument:
    return ResourceDocument(
        business_id=BUSINESS_ID,
        kind=ResourceKind.TABLE,
        name=ResourceName(name),
        capacity=ResourceCapacity(4),
        is_active=is_active,
    )


def test_name_resources_then_services_and_dishes_with_their_approved_titles() -> None:
    keywords = collect_asr_keywords(
        NAME,
        [resource("Terrace"), resource("Broken table", is_active=False)],
        [
            item("Mtsvadi", aliases=(("ru", "Мцвади", KnowledgeAliasStatus.APPROVED),)),
            item(
                "Khachapuri Adjaruli",
                aliases=(
                    ("ka", "აჭარული ხაჭაპური", KnowledgeAliasStatus.APPROVED),
                    ("ru", "Хачапури", KnowledgeAliasStatus.SUGGESTED),
                    ("de", "Käsebrot", KnowledgeAliasStatus.APPROVED),
                ),
            ),
            item("Wine tasting", kind=KnowledgeItemKind.SERVICE),
            item("Is there parking?", kind=KnowledgeItemKind.FAQ),
            item("Old dish", is_active=False),
        ],
        LANGUAGES,
    )

    assert [str(keyword) for keyword in keywords] == [
        "Café Rustaveli",
        "Terrace",
        "Wine tasting",
        "Khachapuri Adjaruli",
        "აჭარული ხაჭაპური",
        "Mtsvadi",
        "Мцвади",
    ]


def test_repeats_long_phrases_and_odd_spacing_are_cleaned() -> None:
    keywords = collect_asr_keywords(
        NAME,
        [resource("café rustaveli"), resource("  Nino\n Beridze  ")],
        [
            item("x" * 61),
            item("MTSVADI", kind=KnowledgeItemKind.PRODUCT),
            item("Mtsvadi"),
        ],
        LANGUAGES,
    )

    assert [str(keyword) for keyword in keywords] == [
        "Café Rustaveli",
        "Nino Beridze",
        "Mtsvadi",
    ]


def test_only_the_top_items_and_at_most_the_cap() -> None:
    many = [item(f"Dish {number:03d}") for number in range(80)]

    top = collect_asr_keywords(NAME, [], many, LANGUAGES)
    assert len(top) == 1 + MAX_KEYWORD_ITEMS
    assert str(top[-1]) == f"Dish {MAX_KEYWORD_ITEMS - 1:03d}"

    resources = [resource(f"Master {number:03d}") for number in range(200)]
    capped = collect_asr_keywords(NAME, resources, many, LANGUAGES)
    assert len(capped) == MAX_ASR_KEYWORDS
