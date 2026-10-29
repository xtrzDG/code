"""
What the customers and the assistant of a load-test history say: short
everyday lines per language (the business's default language picks the
pool; English otherwise). The load tests read lists and cards, so the
texts only need realistic lengths and scripts.
"""

CUSTOMER_LINES: dict[str, tuple[str, ...]] = {
    "en": (
        "Hello! Are you open tonight?",
        "Do you have a table for four at eight?",
        "How much is the set lunch?",
        "Can I bring my dog?",
        "Is there parking nearby?",
        "I would like to move my booking to Saturday.",
        "Thank you, see you then!",
        "Do you have anything vegetarian?",
    ),
    "ru": (
        "Здравствуйте! Вы сегодня работаете?",
        "Есть столик на четверых в восемь?",
        "Сколько стоит бизнес-ланч?",
        "Можно прийти с собакой?",
        "Рядом есть парковка?",
        "Хочу перенести бронь на субботу.",
        "Спасибо, до встречи!",
        "А что есть вегетарианского?",
    ),
    "de": (
        "Hallo! Haben Sie heute Abend geöffnet?",
        "Haben Sie morgen um zehn einen Termin frei?",
        "Was kostet ein Haarschnitt?",
        "Kann ich mit Karte bezahlen?",
        "Gibt es Parkplätze in der Nähe?",
        "Ich möchte meinen Termin auf Samstag verschieben.",
        "Danke, bis dann!",
        "Färben Sie auch?",
    ),
}
ASSISTANT_LINES: dict[str, tuple[str, ...]] = {
    "en": (
        "Hello! Yes, we are open today until 23:00.",
        "Let me check… a table for four at 20:00 is free. Shall I book it?",
        "The set lunch is 25 GEL on weekdays from 12:00 to 16:00.",
        "Dogs are welcome on the terrace.",
        "There is a public car park two minutes away on foot.",
        "Done: your booking is now on Saturday at the same time.",
        "You are welcome! See you soon.",
        "Yes: we have several vegetarian dishes, for example lobio and pkhali.",
    ),
    "ru": (
        "Здравствуйте! Да, сегодня работаем до 23:00.",
        "Проверяю… столик на четверых в 20:00 свободен. Забронировать?",
        "Бизнес-ланч — 25 лари по будням с 12:00 до 16:00.",
        "С собакой можно на террасу.",
        "В двух минутах пешком есть городская парковка.",
        "Готово: бронь перенесена на субботу на то же время.",
        "Пожалуйста! Ждём вас.",
        "Да, есть вегетарианские блюда: например, лобио и пхали.",
    ),
    "de": (
        "Hallo! Ja, heute haben wir bis 20 Uhr geöffnet.",
        "Ich sehe nach… morgen um 10 Uhr ist frei. Soll ich buchen?",
        "Ein Damenhaarschnitt kostet ab 48 Euro.",
        "Ja, Sie können bar oder mit Karte bezahlen.",
        "Ein Parkhaus ist zwei Gehminuten entfernt.",
        "Erledigt: Ihr Termin ist jetzt am Samstag zur gleichen Zeit.",
        "Gern! Bis bald.",
        "Ja, wir färben und beraten Sie gern dazu.",
    ),
}
CUSTOMER_NAMES: tuple[str, ...] = (
    "Nino",
    "Giorgi",
    "Anna",
    "Lukas",
    "Maria",
    "David",
    "Sofia",
    "Jonas",
    "Elena",
    "Levan",
)


def lines_for(language: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The customer and assistant lines of a language (English otherwise)."""

    base: str = language.split("-", 1)[0].lower()
    if base not in CUSTOMER_LINES:
        base = "en"

    return CUSTOMER_LINES[base], ASSISTANT_LINES[base]
