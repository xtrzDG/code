"""
The call greeting of a business that records calls: AI and recording
disclosure with the way to go on without a recording (every country),
operator, the first layer of the privacy notice, languages and openers
(recording off: test_call_greeting_without_recording.py; the countries:
test_call_greeting_countries.py).
"""

import pytest

from app.registries.localization.language_support_data import TEXT_SUPPORTED_LANGUAGES
from app.schemas.dto.conversations import CallGreetingRequest
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.assistant_texts.ai_disclosure_texts import (
    AI_DISCLOSURE,
)
from app.utilities.conversations.assistant_texts.call_consent_texts import (
    CALL_RECORDING_CONSENT,
)
from app.utilities.conversations.assistant_texts.call_texts import (
    CALL_GREETING,
    CALL_OPERATOR_HINT,
)
from tests.brain.brain_world import build_world
from tests.brain.business_setups import BusinessSetup
from tests.brain.call_recording_settings import record_calls
from tests.brain.scripted_turns import scripted


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (
            None,
            "გამარჯობა! ეს არის Sakhli-ის AI-ასისტენტი. საუბარი იწერება. "
            "თუ არ გსურთ ჩაწერა, უბრალოდ თქვით და გავაგრძელებთ ჩაწერის გარეშე. "
            "თანამშრომელთან სასაუბროდ თქვით „ოპერატორი“. "
            "Sakhli პასუხისმგებელია თქვენს მონაცემებზე და მათ მხოლოდ თქვენი "
            "მოთხოვნის შესასრულებლად იყენებს. კონფიდენციალურობის სრული "
            "პოლიტიკისთვის მთხოვეთ ბმული ან ეწვიეთ ჩვენს ვებგვერდს.",
        ),
        (
            "ru",
            "Здравствуйте! Это AI-ассистент «Sakhli». Разговор записывается. "
            "Если вы не хотите, чтобы его записывали, просто скажите об этом, и "
            "мы продолжим без записи. Чтобы поговорить с сотрудником, скажите "
            "«оператор». «Sakhli» отвечает за ваши данные и использует их только "
            "для вашего обращения. Чтобы получить полную политику "
            "конфиденциальности, попросите у меня ссылку или откройте нашу "
            "веб-страницу.",
        ),
        (
            "en",
            "Hello! This is the AI assistant of Sakhli. The call is recorded. If "
            "you do not want it recorded, just say so and we will continue without "
            'a recording. To talk to a staff member, say "operator". Sakhli is '
            "responsible for your data and uses it only to handle your request. "
            "For the full privacy notice, ask me for the link or see our web page.",
        ),
        (
            "it",
            "Buongiorno! Risponde l'assistente IA di Sakhli. La chiamata viene "
            "registrata. Se non desidera la registrazione, lo dica pure e "
            "continueremo senza registrare. Per parlare con un membro dello "
            "staff, dica «operatore». Sakhli è titolare del trattamento dei suoi "
            "dati e li usa solo per gestire la sua richiesta. Per l'informativa "
            "privacy completa, mi chieda il link o consulti la nostra pagina web.",
        ),
        (
            "he",
            "שלום! כאן עוזר ה-AI של Sakhli. השיחה מוקלטת. אם אינכם רוצים "
            "שהשיחה תוקלט, פשוט אמרו זאת ונמשיך בלי הקלטה. "
            'כדי לדבר עם נציג, אמרו "נציג". '
            "Sakhli אחראי על הנתונים שלכם ומשתמש בהם רק כדי לטפל בפנייה שלכם. "
            "להודעת הפרטיות המלאה, בקשו ממני את הקישור או עיינו בדף האינטרנט "
            "שלנו.",
        ),
        (
            "ar",
            "مرحبًا! معك مساعد الذكاء الاصطناعي لدى Sakhli. يتم تسجيل المكالمة. "
            "إذا كنت لا ترغب في تسجيلها، فأخبرنا فقط وسنواصل دون تسجيل. "
            'للتحدث مع أحد الموظفين، قل "موظف". '
            "Sakhli مسؤول عن بياناتك ويستخدمها فقط لمعالجة طلبك. للاطلاع على "
            "إشعار الخصوصية الكامل، اطلب مني الرابط أو تفضّل بزيارة صفحتنا على "
            "الإنترنت.",
        ),
        (
            "sw",
            "Habari! Huyu ni msaidizi wa AI wa Sakhli. Simu hii inarekodiwa. "
            "Ikiwa hutaki irekodiwe, sema tu na tutaendelea bila kurekodi. "
            "Ili kuzungumza na mfanyakazi, sema “opereta”. "
            "Sakhli inawajibika kwa data yako na inaitumia tu kushughulikia "
            "ombi lako. Kwa taarifa kamili ya faragha, niombe kiungo au tembelea "
            "ukurasa wetu wa wavuti.",
        ),
        (
            "ko",
            "안녕하세요! Sakhli의 AI 어시스턴트입니다. 이 통화는 녹음됩니다. "
            "녹음을 원하지 않으시면 말씀해 주세요. 녹음 없이 계속하겠습니다. "
            "직원과 통화하시려면 “상담원”이라고 말씀해 주세요. "
            "Sakhli은(는) 고객님의 정보에 책임을 지며, 요청을 처리하는 데에만 "
            "사용합니다. 전체 개인정보 처리방침은 저에게 링크를 요청하시거나 저희 "
            "웹페이지에서 확인하실 수 있습니다.",
        ),
    ],
)
def test_call_greeting_discloses_the_ai_recording_and_the_operator(
    language: str | None,
    expected: str,
) -> None:
    # A business of the greeting's language alone: no other language to offer.
    world = build_world(scripted(), BusinessSetup(languages=(language or "ka",)))
    record_calls(world)

    greeting = world.greeting.run(
        CallGreetingRequest(
            business_id=world.business.id,
            language=None if language is None else LanguageTag(language),
        )
    )

    assert greeting.text == expected
    assert greeting.language == (language or "ka")


def test_the_greeting_offers_the_other_languages_of_the_business() -> None:
    world = build_world(scripted())  # Georgian, Russian and English.
    record_calls(world)

    def greeting(language: str) -> str:
        return str(
            world.greeting.run(
                CallGreetingRequest(
                    business_id=world.business.id, language=LanguageTag(language)
                )
            ).text
        )

    assert greeting("en").startswith(
        "Hello! This is the AI assistant of Sakhli. I can also speak other "
        "languages: Georgian and Russian. Just answer in the language you "
        "prefer. The call is recorded. If you do not want it recorded"
    )
    assert "სხვა ენებზეც ვსაუბრობ: რუსული და ინგლისური." in greeting("ka")
    # A greeting outside the business's languages offers them all, in its own language.
    assert "altre lingue: georgiano, russo e inglese." in greeting("it")
    # No offer text in Swahili: the greeting stays in one language.
    assert "Habari! Huyu ni msaidizi wa AI wa Sakhli. Simu hii" in greeting("sw")


def test_a_business_of_one_language_offers_none() -> None:
    world = build_world(scripted(), BusinessSetup(languages=("en",)))
    record_calls(world)

    greeting = world.greeting.run(
        CallGreetingRequest(business_id=world.business.id, language=LanguageTag("en"))
    )

    assert greeting.text.startswith(
        "Hello! This is the AI assistant of Sakhli. The call is recorded."
    )


def test_a_language_without_a_greeting_is_greeted_and_labelled_in_english() -> None:
    world = build_world(scripted())
    record_calls(world)

    greeting = world.greeting.run(
        CallGreetingRequest(business_id=world.business.id, language=LanguageTag("yo"))
    )

    assert greeting.text.startswith("Hello! This is the AI assistant of Sakhli.")
    assert greeting.language == "en"


def test_greeting_of_an_unknown_business_is_not_found() -> None:
    world = build_world(scripted())
    record_calls(world)

    with pytest.raises(NotFoundError):
        world.greeting.run(CallGreetingRequest(business_id=BusinessId()))


@pytest.mark.parametrize(
    "text",
    [
        AI_DISCLOSURE,
        CALL_GREETING,
        CALL_RECORDING_CONSENT,
        CALL_OPERATOR_HINT,
    ],
)
def test_customer_facing_openers_exist_in_every_supported_text_language(
    text: LocalizedText,
) -> None:
    missing = sorted(
        str(tag) for tag in TEXT_SUPPORTED_LANGUAGES if tag not in text.values
    )

    assert missing == []
