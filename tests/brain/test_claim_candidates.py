"""The claim check's pre-filter: policy and availability claims per language."""

import pytest

from app.schemas.constants.reply_safety import ClaimTopic
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.reply_guard.claim_candidates import MAX_CLAIMS, find_claim_candidates


def claims(text: str, *tags: str) -> list[tuple[str, ClaimTopic]]:
    return [
        (str(candidate.claim), candidate.topic)
        for candidate in find_claim_candidates(text, [LanguageTag(tag) for tag in tags])
    ]


@pytest.mark.parametrize(
    ("text", "tag", "topic"),
    [
        ("Parking is free for our guests.", "en", ClaimTopic.POLICY),
        ("A table is available at 19:00.", "en", ClaimTopic.AVAILABILITY),
        ("Мы принимаем собак.", "ru", ClaimTopic.POLICY),
        ("Столик на 19:00 свободен.", "ru", ClaimTopic.AVAILABILITY),
        ("Сніданок включено у вартість.", "uk", ClaimTopic.POLICY),
        ("უფასო Wi-Fi გვაქვს.", "ka", ClaimTopic.POLICY),
        ("წინასწარ გადახდა არ არის საჭირო.", "ka", ClaimTopic.POLICY),
        ("Kahvaltı fiyata dahildir.", "tr", ClaimTopic.POLICY),
        ("Saat 19:00 için masa müsait.", "tr", ClaimTopic.AVAILABILITY),
        ("החניה בחינם.", "he", ClaimTopic.POLICY),
        ("الموقف مجاني للضيوف.", "ar", ClaimTopic.POLICY),
        ("Das Frühstück ist inklusive.", "de", ClaimTopic.POLICY),
        ("Le petit-déjeuner est inclus.", "fr", ClaimTopic.POLICY),
        ("El desayuno está incluido.", "es", ClaimTopic.POLICY),
    ],
)
def test_claims_are_found_in_every_language(
    text: str, tag: str, topic: ClaimTopic
) -> None:
    assert claims(text, tag) == [(text, topic)]


@pytest.mark.parametrize(
    ("text", "tag"),
    [
        ("Would you like free parking?", "en"),
        ("Хотите бесплатную парковку?", "ru"),
        ("هل تريد موقفا مجانيا؟", "ar"),
        ("Thank you, see you tomorrow at 19:00.", "en"),
        ("Am Freitag sind wir ab 10 Uhr da.", "de"),
    ],
)
def test_questions_and_plain_sentences_are_no_claims(text: str, tag: str) -> None:
    assert claims(text, tag) == []


def test_english_markers_apply_to_every_conversation() -> None:
    assert claims("Wi-Fi is free.", "ka") == [("Wi-Fi is free.", ClaimTopic.POLICY)]


def test_at_most_five_claims_are_checked() -> None:
    text = " ".join(f"Option {index} is free." for index in range(8))

    assert len(claims(text, "en")) == MAX_CLAIMS
