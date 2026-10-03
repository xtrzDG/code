import pytest

from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.language_detector import LanguageDetector

ALL_CANDIDATES: list[LanguageTag] = [
    LanguageTag(tag)
    for tag in (
        "ka",
        "ru",
        "en",
        "uk",
        "he",
        "ar",
        "hy",
        "tr",
        "de",
        "pt-BR",
        "zh",
        "ja",
        "az",
        "pl",
        "fr",
        "es",
        "it",
        "kk",
        "fa",
        "vi",
        "ro",
        "nl",
        "id",
        "bg",
        "sr",
        "be",
        "el",
        "th",
        "hi",
        "ko",
    )
]
DETECTOR = LanguageDetector()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("გამარჯობა, ხვალ საღამოს მაგიდა მინდა", "ka"),
        ("Здравствуйте! Хочу забронировать столик на завтра", "ru"),
        ("Hi, can I book a table for tomorrow evening?", "en"),
        ("Привіт! Хочу забронювати столик на завтра", "uk"),
        ("שלום, אפשר להזמין שולחן למחר בערב?", "he"),
        ("مرحبا، أريد حجز طاولة غدا مساء", "ar"),
        ("Բարև Ձեզ, ուզում եմ վաղը սեղան ամրագրել", "hy"),
        ("Merhaba, yarın akşam için masa istiyorum", "tr"),
        ("Hallo, ich möchte einen Tisch für morgen reservieren", "de"),
        ("Olá, quero reservar uma mesa para amanhã", "pt-BR"),
        ("你好，我想预订明天晚上的桌子", "zh"),
        ("こんにちは、明日の夜にテーブルを予約したいです", "ja"),
        ("Salam, sabah axşam üçün masa istəyirəm", "az"),
        ("Dzień dobry, chciałbym zarezerwować stolik na jutro", "pl"),
        ("Bonjour, je voudrais réserver une table pour demain soir", "fr"),
        ("Hola, quiero reservar una mesa para mañana", "es"),
        ("Ciao, vorrei prenotare un tavolo per domani sera", "it"),
        ("Сәлеметсіз бе, ертеңге үстел керек", "kk"),
        ("سلام، می خواهم برای فردا میز رزرو کنم", "fa"),
        ("Xin chào, tôi muốn đặt bàn cho ngày mai", "vi"),
        ("Bună ziua, aș vrea o masă pentru mâine", "ro"),
        ("Hallo, ik wil graag een tafel reserveren voor morgen", "nl"),
        ("Halo, saya mau pesan meja untuk besok", "id"),
        ("Здравейте, искам маса за утре вечер", "bg"),
        ("Здраво, хвала, треба ми сто за сутра", "sr"),
        ("Прывітанне, хачу столік на заўтра", "be"),
        ("Γεια σας, θέλω ένα τραπέζι για αύριο", "el"),
        ("สวัสดีครับ ต้องการจองโต๊ะพรุ่งนี้", "th"),
        ("नमस्ते, मुझे कल के लिए टेबल चाहिए", "hi"),
        ("안녕하세요, 내일 테이블 예약하고 싶어요", "ko"),
    ],
)
def test_detects_the_language_of_a_first_message(text: str, expected: str) -> None:
    assert DETECTOR.detect(text, ALL_CANDIDATES, LanguageTag("en")) == expected


def test_only_candidate_languages_are_returned() -> None:
    georgian_business = [LanguageTag("ka"), LanguageTag("ru"), LanguageTag("en")]

    assert DETECTOR.detect("Hola, una mesa", georgian_business, LanguageTag("ka")) == (
        "en"
    )
    assert DETECTOR.detect("Привіт, столик", georgian_business, LanguageTag("ka")) == (
        "ru"
    )
    assert DETECTOR.detect("שלום", georgian_business, LanguageTag("ka")) == "ka"


def test_base_language_selects_the_regional_candidate() -> None:
    candidates = [LanguageTag("es"), LanguageTag("pt-BR"), LanguageTag("en")]

    assert DETECTOR.detect(
        "Obrigado, quanto custa?", candidates, LanguageTag("es")
    ) == ("pt-BR")


@pytest.mark.parametrize("text", ["", "123", "👍👍", "!!!", "+995 555 12 34 56"])
def test_text_without_letters_falls_back(text: str) -> None:
    assert DETECTOR.detect(text, ALL_CANDIDATES, LanguageTag("ka")) == "ka"


def test_unclear_latin_text_prefers_the_fallback_among_tied_candidates() -> None:
    candidates = [LanguageTag("de"), LanguageTag("en"), LanguageTag("nl")]

    assert DETECTOR.detect("OK", candidates, LanguageTag("nl")) == "nl"
    assert DETECTOR.detect("OK", candidates, LanguageTag("ka")) == "de"


def test_han_text_without_kana_is_chinese_and_with_kana_japanese() -> None:
    candidates = [LanguageTag("ja"), LanguageTag("zh-Hant"), LanguageTag("en")]

    assert DETECTOR.detect("明天", candidates, LanguageTag("en")) == "zh-Hant"
    assert DETECTOR.detect("明日の予約です", candidates, LanguageTag("en")) == "ja"
    assert DETECTOR.detect("明天", [LanguageTag("ja")], LanguageTag("en")) == "ja"


def test_mixed_scripts_follow_the_majority() -> None:
    candidates = [LanguageTag("ka"), LanguageTag("ru"), LanguageTag("en")]

    assert (
        DETECTOR.detect(
            "Hello, хочу столик на завтра вечером", candidates, LanguageTag("ka")
        )
        == "ru"
    )


def test_serbian_in_latin_script_is_not_judged_by_cyrillic_letters() -> None:
    candidates = [LanguageTag("sr-Latn"), LanguageTag("en")]

    assert (
        DETECTOR.detect("Hvala, sto za sutra", candidates, LanguageTag("en"))
        in candidates
    )


@pytest.mark.parametrize(
    ("text", "candidates", "fallback", "expected"),
    [
        (
            "நாளை இரவு 7 மணிக்கு இரண்டு பேருக்கு மேசை வேண்டும்",
            ("si", "ta", "en"),
            "si",
            "ta",
        ),
        ("හෙට රෑ 7ට මේසයක් ඕනේ", ("ta", "si", "en"), "ta", "si"),
        ("আমি কাল 7pm এ table বুক করতে চাই", ("bn", "en"), "en", "bn"),
        ("আমি কাল একটি টেবিল বুক করতে চাই", ("bn", "en"), "en", "bn"),
        ("ነገ ጠረጴዛ ማስያዝ እፈልጋለሁ", ("am", "en"), "en", "am"),
        ("ខ្ញុំចង់កក់តុមួយ", ("km", "en"), "en", "km"),
        ("ຂ້ອຍຢາກຈອງໂຕະ", ("lo", "en"), "en", "lo"),
        ("မနက်ဖြန် စားပွဲ ကြိုတင်မှာချင်ပါတယ်", ("my", "en"), "en", "my"),
        ("ข้าวผัดราคาเท่าไหร่ table", ("th", "en"), "en", "th"),
    ],
)
def test_scripts_of_south_and_southeast_asia_and_ethiopia_are_recognized(
    text: str,
    candidates: tuple[str, ...],
    fallback: str,
    expected: str,
) -> None:
    detected = LanguageDetector().detect(
        text,
        [LanguageTag(tag) for tag in candidates],
        LanguageTag(fallback),
    )

    assert detected == expected
