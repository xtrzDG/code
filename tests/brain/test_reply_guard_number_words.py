"""Numbers written in words: read next to currency, percent and time words."""

import pytest

from tests.brain.reply_guard_helpers import mentions, unverified

PRICE_EVIDENCE: list[str] = ["Parking: 40 GEL per day", "Hours: 09:00-21:00"]


@pytest.mark.parametrize(
    ("reply", "tag", "expected"),
    [
        ("Parking costs fifty lari a day.", "en", "fifty lari"),
        ("Парковка стоит пятьдесят лари.", "ru", "пятьдесят лари"),
        ("პარკინგი ორმოცდაათი ლარი ღირს.", "ka", "ორმოცდაათი ლარი"),
        ("პარკინგი ორმოცდაათ ლარად.", "ka", "ორმოცდაათ ლარად"),
        ("Паркування коштує п'ятдесят ларі.", "uk", "п'ятдесят ларі"),
        ("Otopark günlük elli lari.", "tr", "elli lari"),
        ("החניה עולה חמישים לארי ליום.", "he", "חמישים לארי"),
        ("الموقف بخمسين لاري في اليوم.", "ar", "بخمسين لاري"),
        ("Das Parken kostet fünfzig Lari.", "de", "fünfzig Lari"),
        ("Le parking coûte cinquante lari.", "fr", "cinquante lari"),
        ("El parking cuesta cincuenta lari.", "es", "cincuenta lari"),
    ],
)
def test_an_invented_price_in_words_is_caught_in_every_language(
    reply: str, tag: str, expected: str
) -> None:
    assert unverified(reply, PRICE_EVIDENCE, "GEL", tag) == [expected]


@pytest.mark.parametrize(
    ("reply", "tag"),
    [
        ("Parking costs forty lari a day.", "en"),
        ("Парковка стоит сорок лари.", "ru"),
        ("პარკინგი ორმოცი ლარი ღირს.", "ka"),
        ("Паркування коштує сорок ларі.", "uk"),
        ("Otopark günlük kırk lari.", "tr"),
        ("החניה עולה ארבעים לארי ליום.", "he"),
        ("الموقف بأربعين لاري في اليوم.", "ar"),
        ("Das Parken kostet vierzig Lari.", "de"),
        ("Le parking coûte quarante lari.", "fr"),
        ("El parking cuesta cuarenta lari.", "es"),
    ],
)
def test_a_price_in_words_backed_by_the_facts_passes(reply: str, tag: str) -> None:
    assert unverified(reply, PRICE_EVIDENCE, "GEL", tag) == []


@pytest.mark.parametrize(
    ("text", "tag", "value"),
    [
        ("One hundred and fifty lari.", "en", 150),
        ("A thousand lari.", "en", 1000),
        ("Две тысячи лари за ночь.", "ru", 2000),
        ("2 тысячи лари за ночь.", "ru", 2000),
        ("двести пятьдесят лари", "ru", 250),
        ("ორას ორმოცდაათი ლარი", "ka", 250),
        ("ათას ხუთასი ლარი", "ka", 1500),
        ("двісті п'ятдесят ларі", "uk", 250),
        ("iki yüz elli lari", "tr", 250),
        ("ikiyüzelli lari", "tr", 250),
        ("מאה וחמישים לארי", "he", 150),
        ("חמש עשרה לארי", "he", 15),
        ("خمسة وعشرون لاري", "ar", 25),
        ("ثلاثمائة لاري", "ar", 300),
        ("zweihundertfünfundzwanzig Lari", "de", 225),
        ("soixante et onze lari", "fr", 71),
        ("quatre-vingt-dix lari", "fr", 90),
        ("vingt-et-un lari", "fr", 21),
        ("treinta y cinco lari", "es", 35),
        ("doscientos cincuenta lari", "es", 250),
        ("dos mil lari", "es", 2000),
    ],
)
def test_compound_numbers_read_as_one_amount(text: str, tag: str, value: int) -> None:
    (mention,) = mentions(text, "GEL", tag)

    assert mention.is_money is True
    assert {int(amount) for amount in mention.amounts} == {value}


@pytest.mark.parametrize(
    ("reply", "tag", "expected"),
    [
        ("We give twenty percent off.", "en", "twenty percent"),
        ("Скидка двадцать процентов.", "ru", "двадцать процентов"),
        ("ფასდაკლება ოცი პროცენტი.", "ka", "ოცი პროცენტი"),
        ("Знижка двадцять відсотків.", "uk", "двадцять відсотків"),
        ("Yüzde yirmi indirim.", "tr", "Yüzde yirmi"),
        ("הנחה של עשרים אחוז.", "he", "עשרים אחוז"),
        ("خصم عشرين في المئة.", "ar", "عشرين في المئة"),
        ("Zwanzig Prozent Rabatt.", "de", "Zwanzig Prozent"),
        ("Une remise de vingt pour cent.", "fr", "vingt pour cent"),
        ("Un descuento del veinte por ciento.", "es", "veinte por ciento"),
    ],
)
def test_percentages_in_words_need_the_facts(
    reply: str, tag: str, expected: str
) -> None:
    assert unverified(reply, PRICE_EVIDENCE, "GEL", tag) == [expected]


@pytest.mark.parametrize(
    ("reply", "tag", "expected"),
    [
        ("We open at seven.", "en", "at seven"),
        ("Мы открываемся в семь.", "ru", "в семь"),
        ("შვიდ საათზე ვიხსნებით.", "ka", "შვიდ საათზე"),
        ("Ми відкриваємося о сьомій, приходьте о сім годин.", "uk", "сім годин"),
        ("Saat yedide açılıyoruz.", "tr", "Saat yedide"),
        ("אנחנו נפתחים בשעה שבע.", "he", "בשעה שבע"),
        ("نفتح الساعة السابعة.", "ar", "الساعة السابعة"),
        ("Wir öffnen um sieben Uhr.", "de", "um sieben Uhr"),
        ("Nous ouvrons à sept heures.", "fr", "à sept heures"),
        ("Abrimos a las siete.", "es", "las siete"),
    ],
)
def test_an_invented_hour_in_words_is_caught(
    reply: str, tag: str, expected: str
) -> None:
    assert unverified(reply, PRICE_EVIDENCE, "GEL", tag) == [expected]


@pytest.mark.parametrize(
    ("reply", "tag"),
    [
        ("We open at nine.", "en"),
        ("Мы закрываемся в девять.", "ru"),
        ("Abrimos a las nueve.", "es"),
        ("Wir öffnen um neun Uhr.", "de"),
    ],
)
def test_an_hour_in_words_backed_by_the_hours_passes(reply: str, tag: str) -> None:
    # "nine" reads as 09:00 and 21:00; both are in "09:00-21:00".
    assert unverified(reply, PRICE_EVIDENCE, "GEL", tag) == []


@pytest.mark.parametrize(
    ("reply", "tag"),
    [
        ("We have two halls and one terrace.", "en"),
        ("Meet us at one of our branches.", "en"),
        ("Fifty guests fit in the main hall.", "en"),
        ("У нас два зала и одна терраса.", "ru"),
        ("Book at least two days ahead.", "en"),
    ],
)
def test_counts_in_words_are_not_checked(reply: str, tag: str) -> None:
    assert unverified(reply, PRICE_EVIDENCE, "GEL", tag) == []


def test_number_words_in_the_facts_back_digits_in_the_reply() -> None:
    evidence: list[str] = ["Parking: fifty lari a day", "Room: двести лари"]

    assert (
        unverified("Parking is 50 GEL, the room 200 ₾.", evidence, "GEL", "en", "ru")
        == []
    )


def test_words_of_another_language_do_not_glue_onto_a_number() -> None:
    # "on" is ten in Turkish; "on fifty lari" is fifty, not sixty.
    found = mentions("Pay on fifty lari.", "GEL", "en", "tr")

    assert [(item.text, sorted(item.amounts)) for item in found] == [
        ("fifty lari", [50])
    ]


def test_customer_words_never_back_a_price_in_words() -> None:
    assert unverified(
        "Fine, fifty lari then.",
        PRICE_EVIDENCE,
        "GEL",
        "en",
        customer=["Can I pay fifty lari?"],
    ) == ["fifty lari"]
