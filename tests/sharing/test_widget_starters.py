"""The website chat's starter questions, taken from the business's FAQ."""

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.menu_import.prefixed_id import MenuImportBatchId
from app.utilities.channels.widget_starters import build_starter_questions
from app.utilities.conversations.language_detector import LanguageDetector

BUSINESS = BusinessId("business_0b6c2f5e-1d1a-4c55-9a3e-2f1d5b7c9e01")
LANGUAGES = [LanguageTag("ka"), LanguageTag("ru"), LanguageTag("en")]


def faq(
    title: str,
    languages: list[str] | None = None,
    kind: KnowledgeItemKind = KnowledgeItemKind.FAQ,
    is_active: bool = True,
    is_draft: bool = False,
) -> KnowledgeItemDocument:
    return KnowledgeItemDocument(
        business_id=BUSINESS,
        kind=kind,
        title=KnowledgeTitle(title),
        languages=[LanguageTag(tag) for tag in languages or []],
        is_active=is_active,
        import_batch_id=MenuImportBatchId() if is_draft else None,
    )


def starters(items: list[KnowledgeItemDocument]) -> list[tuple[str, str]]:
    return [
        (str(starter.language), str(starter.text))
        for starter in build_starter_questions(
            items, LANGUAGES, LanguageTag("ka"), LanguageDetector()
        )
    ]


def test_questions_are_sorted_into_the_language_they_are_written_in() -> None:
    assert starters(
        [
            faq("Есть ли парковка?"),
            faq("Do you deliver?"),
            faq("გაქვთ პარკინგი?"),
        ]
    ) == [
        ("ru", "Есть ли парковка?"),
        ("en", "Do you deliver?"),
        ("ka", "გაქვთ პარკინგი?"),
    ]


def test_at_most_three_per_language_in_the_owners_order() -> None:
    questions = [f"Question number {number}?" for number in range(1, 6)]

    assert starters([faq(question, ["en"]) for question in questions]) == [
        ("en", question) for question in questions[:3]
    ]


def test_named_languages_win_over_detection() -> None:
    assert starters([faq("Wi-Fi?", ["ka", "en"])]) == [
        ("ka", "Wi-Fi?"),
        ("en", "Wi-Fi?"),
    ]


def test_only_active_confirmed_short_faq_questions_become_starters() -> None:
    assert starters(
        [
            faq("Hidden question?", ["en"], is_active=False),
            faq("Imported, not confirmed?", ["en"], is_draft=True),
            faq("Khachapuri", ["en"], kind=KnowledgeItemKind.MENU_ITEM),
            faq("A question far too long " * 5, ["en"]),
            # A language the business does not speak: detected among its own.
            faq("Do you speak French?", ["fr"]),
            faq("Do you take cards?", ["en"]),
        ]
    ) == [("en", "Do you speak French?"), ("en", "Do you take cards?")]
