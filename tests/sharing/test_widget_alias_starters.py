"""
Starter questions in the visitor's language from the aliases the owner
approved: a Russian FAQ gives chips in Georgian and English too, before the
niche's own questions fill a language that still has none.
"""

from app.schemas.constants.knowledge import KnowledgeAliasStatus, KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeAlias, KnowledgeItemDocument
from app.schemas.dto.channels.widget import WidgetStarterQuestionView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAliasText
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.widget_starters import (
    add_niche_starters,
    build_starter_questions,
)
from app.utilities.conversations.language_detector import LanguageDetector
from tests.sharing.test_widget_niche_starters import RESTAURANT_FAQ

BUSINESS = BusinessId("business_7a1e4c52-9d0b-4b39-8f5e-0c2a6d3e1f44")
LANGUAGES = [LanguageTag("ka"), LanguageTag("ru"), LanguageTag("en"), LanguageTag("he")]
APPROVED = KnowledgeAliasStatus.APPROVED
SUGGESTED = KnowledgeAliasStatus.SUGGESTED


def faq(
    title: str, *aliases: tuple[str, str, KnowledgeAliasStatus]
) -> KnowledgeItemDocument:
    return KnowledgeItemDocument(
        business_id=BUSINESS,
        kind=KnowledgeItemKind.FAQ,
        title=KnowledgeTitle(title),
        languages=[LanguageTag("ru")],
        aliases=[
            KnowledgeAlias(
                language=LanguageTag(language),
                text=KnowledgeAliasText(text),
                status=status,
            )
            for language, text, status in aliases
        ],
    )


def chips(items: list[KnowledgeItemDocument]) -> list[WidgetStarterQuestionView]:
    return build_starter_questions(
        items, LANGUAGES, LanguageTag("ka"), LanguageDetector()
    )


def by_language(starters: list[WidgetStarterQuestionView]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for starter in starters:
        grouped.setdefault(str(starter.language), []).append(str(starter.text))
    return grouped


def test_a_russian_faq_gives_chips_in_three_languages_from_approved_aliases() -> None:
    starters = chips(
        [
            faq(
                "Есть ли парковка?",
                ("ka", "გაქვთ პარკინგი?", APPROVED),
                ("en", "Do you have parking?", APPROVED),
                ("he", "יש חניה?", SUGGESTED),
            ),
            faq(
                "Можно ли прийти с детьми?",
                ("ka", "შეიძლება ბავშვებთან ერთად მოსვლა?", APPROVED),
                ("en", "Can I come with children?", SUGGESTED),
            ),
        ]
    )

    assert by_language(starters) == {
        "ru": ["Есть ли парковка?", "Можно ли прийти с детьми?"],
        "ka": ["გაქვთ პარკინგი?", "შეიძლება ბავშვებთან ერთად მოსვლა?"],
        "en": ["Do you have parking?"],
    }


def test_the_first_approved_alias_of_a_language_is_the_chip_and_three_at_most() -> None:
    questions = [
        faq(
            f"Вопрос номер {number}?",
            ("en", f"Question number {number}?", APPROVED),
            ("en", f"Another way to ask {number}?", APPROVED),
        )
        for number in range(1, 5)
    ]

    assert by_language(chips(questions))["en"] == [
        "Question number 1?",
        "Question number 2?",
        "Question number 3?",
    ]


def test_an_alias_too_long_for_a_chip_is_not_offered() -> None:
    long_alias = "Do you have parking " + "near the old town and the river " * 3 + "?"

    assert "en" not in by_language(
        chips([faq("Есть ли парковка?", ("en", long_alias, APPROVED))])
    )


def test_an_approved_alias_wins_over_the_niches_ready_questions() -> None:
    from_faq = chips([faq("Есть ли парковка?", ("ka", "გაქვთ პარკინგი?", APPROVED))])

    starters = by_language(add_niche_starters(from_faq, LANGUAGES, RESTAURANT_FAQ))

    # Georgian has the owner's alias, so the niche's questions stay out of
    # it; English, which has no alias, gets them.
    assert starters["ka"] == ["გაქვთ პარკინგი?"]
    assert starters["en"][0] == "How can I book a table?"
