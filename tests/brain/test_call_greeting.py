"""The call greeting: AI and recording disclosure, operator, languages and openers."""

import pytest

from app.registries.localization.language_support_data import TEXT_SUPPORTED_LANGUAGES
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.conversations import CallGreetingRequest
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.utilities.conversations.assistant_texts.ai_disclosure_texts import (
    AI_DISCLOSURE,
)
from app.utilities.conversations.assistant_texts.call_texts import (
    CALL_GREETING,
    CALL_OPERATOR_HINT,
    CALL_RECORDING_NOTICE,
)
from tests.brain.brain_world import build_world
from tests.brain.business_setups import BusinessSetup
from tests.brain.scripted_turns import scripted


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (
            None,
            "გამარჯობა! ეს არის Sakhli-ის AI-ასისტენტი. საუბარი იწერება. "
            "თანამშრომელთან სასაუბროდ თქვით „ოპერატორი“.",
        ),
        (
            "ru",
            "Здравствуйте! Это AI-ассистент «Sakhli». Разговор записывается. "
            "Чтобы поговорить с сотрудником, скажите «оператор».",
        ),
        (
            "en",
            "Hello! This is the AI assistant of Sakhli. The call is recorded. "
            'To talk to a staff member, say "operator".',
        ),
        (
            "he",
            "שלום! כאן עוזר ה-AI של Sakhli. השיחה מוקלטת. "
            'כדי לדבר עם נציג, אמרו "נציג".',
        ),
        (
            "ar",
            "مرحبًا! معك مساعد الذكاء الاصطناعي لدى Sakhli. يتم تسجيل المكالمة. "
            'للتحدث مع أحد الموظفين، قل "موظف".',
        ),
        (
            "sw",
            "Habari! Huyu ni msaidizi wa AI wa Sakhli. Simu hii inarekodiwa. "
            "Ili kuzungumza na mfanyakazi, sema “opereta”.",
        ),
        (
            "ko",
            "안녕하세요! Sakhli의 AI 어시스턴트입니다. 이 통화는 녹음됩니다. "
            "직원과 통화하시려면 “상담원”이라고 말씀해 주세요.",
        ),
    ],
)
def test_call_greeting_discloses_the_ai_recording_and_the_operator(
    language: str | None,
    expected: str,
) -> None:
    world = build_world(scripted())

    greeting = world.greeting.run(
        CallGreetingRequest(
            business_id=world.business.id,
            language=None if language is None else LanguageTag(language),
        )
    )

    assert greeting.text == expected
    assert greeting.language == (language or "ka")


def test_a_language_without_a_greeting_is_greeted_and_labelled_in_english() -> None:
    world = build_world(scripted())

    greeting = world.greeting.run(
        CallGreetingRequest(business_id=world.business.id, language=LanguageTag("yo"))
    )

    assert greeting.text.startswith("Hello! This is the AI assistant of Sakhli.")
    assert greeting.language == "en"


@pytest.mark.parametrize("country", ["GE", "DE", "US", "ZZ"])
def test_recorded_calls_always_say_so_whatever_the_profile_says(
    country: str,
) -> None:
    world = build_world(
        scripted(),
        BusinessSetup(country_code=country if country != "ZZ" else "GE"),
    )
    profile = world.profile_repo.get_by_business(world.business.id)
    assert isinstance(profile, BusinessProfileDocument)
    profile.is_recording_notice_enabled = False
    world.profile_repo.save(profile)
    if country == "ZZ":
        world.business.country_code = CountryCode("ZZ")
        world.save_business(world.business)

    greeting = world.greeting.run(
        CallGreetingRequest(business_id=world.business.id, language=LanguageTag("en"))
    )

    assert "The call is recorded." in greeting.text


def test_greeting_of_an_unknown_business_is_not_found() -> None:
    world = build_world(scripted())

    with pytest.raises(NotFoundError):
        world.greeting.run(CallGreetingRequest(business_id=BusinessId()))


@pytest.mark.parametrize(
    "text",
    [AI_DISCLOSURE, CALL_GREETING, CALL_RECORDING_NOTICE, CALL_OPERATOR_HINT],
)
def test_customer_facing_openers_exist_in_every_supported_text_language(
    text: LocalizedText,
) -> None:
    missing = sorted(
        str(tag) for tag in TEXT_SUPPORTED_LANGUAGES if tag not in text.values
    )

    assert missing == []
