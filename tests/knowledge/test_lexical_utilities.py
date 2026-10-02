import pytest

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.ranking.character_ngrams import character_ngram_dice
from app.utilities.knowledge.ranking.lexical_ranking import rank_knowledge_items
from app.utilities.knowledge.ranking.price_matching import rank_price_matches
from app.utilities.knowledge.ranking.token_similarity import (
    bounded_edit_distance,
    token_similarity,
)
from app.utilities.knowledge.search_text import (
    SearchToken,
    contains_phrase,
    fold_text,
    fold_words,
    tokenize,
)

BUSINESS_ID: BusinessId = BusinessId()


def word(text: str) -> SearchToken:
    return SearchToken(text=text, weight=1.0, allows_partial=True)


def item(
    title: str,
    body: str | None = None,
    languages: tuple[str, ...] = (),
) -> KnowledgeItemDocument:
    return KnowledgeItemDocument(
        business_id=BUSINESS_ID,
        kind=KnowledgeItemKind.MENU_ITEM,
        title=KnowledgeTitle(title),
        body=None if body is None else KnowledgeBody(body),
        price_minor=MoneyAmountMinor(1000),
        languages=[LanguageTag(language) for language in languages],
    )


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("Café ÉCLAIR", "cafe eclair"),
        ("Ёлка и йогурт", "елка и иогурт"),
        ("Straße", "strasse"),
        ("ᲮᲐᲭᲐᲞᲣᲠᲘ", "ხაჭაპური"),
        ("פִּיצָה", "פיצה"),
        ("מים חמים", "מימ חמימ"),
        ("مُـوقف", "موقف"),
        ("أحمد إسلام آمنة", "احمد اسلام امنه"),
        ("ｶﾌｪ", "カフェ"),
    ],
)
def test_fold_text_removes_case_accents_and_script_variants(
    raw_text: str,
    expected: str,
) -> None:
    assert fold_text(raw_text) == expected


def test_tokenize_splits_words_and_space_less_scripts_into_ngrams() -> None:
    assert [token.text for token in tokenize("Khachapuri, по-аджарски!")] == [
        "khachapuri",
        "по",
        "аджарски",
    ]
    assert [token.text for token in tokenize("iPhone手机壳")] == [
        "iphone",
        "手",
        "机",
        "壳",
        "手机",
        "机壳",
    ]
    assert [token.text for token in tokenize("ราคา")] == [
        "ร",
        "า",
        "ค",
        "า",
        "รา",
        "าค",
        "คา",
    ]
    assert all(not token.allows_partial for token in tokenize("拿铁"))
    assert tokenize("  ,;! ") == []


def test_phrase_matching_respects_word_boundaries_except_in_cjk() -> None:
    assert contains_phrase("margherita pizza", "pizza")
    assert not contains_phrase("steak", "tea")
    assert contains_phrase("冰拿铁", "拿铁")
    assert not contains_phrase("anything", "")
    assert fold_words("  Pizza —  MARGHERITA ") == "pizza margherita"


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ("pizza", "pizza", 1.0),
        ("хачапури", "хачапурис", 0.8),
        ("салат", "салаты", 0.8),
        ("салата", "салаты", 0.7),
        ("latte", "late", 0.6),
        ("capuccino", "cappuccino", 0.6),
        ("wine", "wife", 0.6),
        ("pasta", "pizza", 0.0),
        ("price", "rice", 0.0),
        ("פיצה", "הפיצה", 0.7),
        ("فلافل", "الفلافل", 0.7),
        ("tea", "steak", 0.0),
    ],
)
def test_token_similarity(first: str, second: str, expected: float) -> None:
    assert token_similarity(word(first), word(second)) == expected


def test_ngram_tokens_match_only_exactly() -> None:
    first = SearchToken(text="拿铁", weight=1.0, allows_partial=False)
    second = SearchToken(text="拿铁咖", weight=1.0, allows_partial=False)

    assert token_similarity(first, second) == 0.0


def test_bounded_edit_distance_counts_swaps_and_stops_early() -> None:
    assert bounded_edit_distance("abcd", "abdc", 2) == 1
    assert bounded_edit_distance("kitten", "sitting", 5) == 3
    assert bounded_edit_distance("abcdef", "uvwxyz", 1) == 2


def test_character_ngram_dice() -> None:
    assert character_ngram_dice("pizza", "pizza") == 1.0
    assert character_ngram_dice("wine", "wifi") < 0.3
    assert character_ngram_dice("拿铁", "冰拿铁") > 0.5
    assert character_ngram_dice("", "x") < 1.0


def test_search_prefers_titles_over_bodies_and_rare_words() -> None:
    soup = item("Tomato soup", "With fresh basil")
    salad = item("Caprese salad", "Tomato, mozzarella and basil")
    pizza = item("Pizza Margherita", "Tomato sauce, mozzarella, basil")

    ranked = rank_knowledge_items("tomato soup", [salad, pizza, soup])

    assert [ranked_item.item.title for ranked_item in ranked][0] == "Tomato soup"
    assert {ranked_item.item.title for ranked_item in ranked} == {
        "Tomato soup",
        "Caprese salad",
        "Pizza Margherita",
    }


def test_search_gives_a_small_bonus_to_items_in_the_customer_language() -> None:
    english = item("Parking", "Free parking", languages=("en",))
    russian = item("Parking", "Free parking", languages=("ru-RU",))

    ranked = rank_knowledge_items("parking", [english, russian], ["ru"])

    assert ranked[0].item.id == russian.id
    assert ranked[0].score > ranked[1].score


def test_search_without_matches_or_items_returns_nothing() -> None:
    assert rank_knowledge_items("helicopter", [item("Pizza")]) == []
    assert rank_knowledge_items("pizza", []) == []
    assert rank_knowledge_items("!!!", [item("Pizza")]) == []


def test_price_matching_tolerates_typos_but_not_unrelated_items() -> None:
    items = [item("Latte"), item("Pizza Margherita"), item("House wine")]

    assert [match.item.title for match in rank_price_matches("late", items)] == [
        "Latte"
    ]
    assert [match.item.title for match in rank_price_matches("pizza", items)] == [
        "Pizza Margherita"
    ]
    assert rank_price_matches("pasta", items) == []
    assert rank_price_matches("wifi", items) == []
    assert rank_price_matches("", items) == []


def test_exact_title_scores_highest_in_price_matching() -> None:
    items = [item("Pizza Margherita"), item("Pizza"), item("Pizza Diavola")]

    matches = rank_price_matches("PIZZA", items)

    assert matches[0].item.title == "Pizza"
    assert matches[0].score == 1.0
    assert len(matches) == 3
