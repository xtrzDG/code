"""What the workshop's model says and how it reads customers' intent and language."""

import re

LANGUAGE_TAG_PATTERN: re.Pattern[str] = re.compile(r"language tag ([A-Za-z\-]+)\)")
GOAL_PATTERN: re.Pattern[str] = re.compile(r"^Your goal: (.+)$", re.MULTILINE)

# What the AI customer writes, by scenario language and intent.
CUSTOMER_MESSAGES: dict[str, dict[str, str]] = {
    "ka": {
        "booking": "მინდა მაგიდის დაჯავშნა",
        "price": "რა ღირს ხაჭაპური?",
        "human": "მენეჯერთან დამაკავშირეთ, გთხოვთ",
        "other": "გამარჯობა, კითხვა მაქვს",
    },
    "ru": {
        "booking": "Хочу забронировать столик",
        "price": "Сколько стоит хачапури?",
        "human": "Позовите менеджера, пожалуйста",
        "other": "Здравствуйте, у меня вопрос",
    },
    "en": {
        "booking": "I would like to book a table",
        "price": "How much is khachapuri?",
        "human": "Let me talk to a manager, please",
        "other": "Hello, I have a question",
    },
    # Languages the business does not list (the foreign-language scenarios).
    "he": {"other": "שלום, יש לי שאלה"},
    "de": {"other": "Hallo, ich habe eine Frage"},
}
# What the AI customer of a transliteration scenario writes.
TRANSLITERATED_MESSAGES: dict[str, str] = {
    "ka": "gamarjoba, kitxva makvs",
    "ru": "zdravstvuyte, u menya vopros",
}
TRANSLITERATION_MARKER: str = "Latin letters (transliteration)"
REPLY_LANGUAGE_PATTERN: re.Pattern[str] = re.compile(
    r"^Reply language: .*\(([a-z]{2,3})(?:-[A-Za-z0-9]+)*\)\.", re.MULTILINE
)

# What the assistant answers, in the language the customer wrote in.
ASSISTANT_TEXTS: dict[str, dict[str, str]] = {
    "ka": {
        "greeting": "გამარჯობა! რით შემიძლია დაგეხმაროთ?",
        "booked": "მზადაა! მაგიდა დაჯავშნილია 19:00-ზე.",
        "price": "ხაჭაპურის ფასია {price}.",
        "no_price": "სამწუხაროდ, ფასი ვერ ვიპოვე.",
        "fine": "კარგი.",
    },
    "ru": {
        "greeting": "Здравствуйте! Чем могу помочь?",
        "booked": "Готово, Нино! Ваш столик забронирован на 19:00.",
        "price": "Хачапури стоит {price}.",
        "no_price": "К сожалению, цену не нашёл.",
        "fine": "Хорошо.",
    },
    "en": {
        "greeting": "Hello! How can I help?",
        "booked": "Done! Your table is booked for 19:00.",
        "price": "Khachapuri costs {price}.",
        "no_price": "Sorry, I could not find the price.",
        "fine": "All right.",
    },
    "he": {"greeting": "שלום! איך אפשר לעזור?", "fine": "בסדר."},
    "de": {"greeting": "Hallo! Wie kann ich helfen?", "fine": "In Ordnung."},
}
HANDOFF_WORDS: tuple[str, ...] = ("менеджер", "მენეჯერ", "manager")
BOOKING_WORDS: tuple[str, ...] = ("забронировать", "დაჯავშნა", "book a table")
PRICE_WORDS: tuple[str, ...] = ("ღირს", "Сколько стоит", "How much")


def read_customer_intent(goal: str) -> str:
    """The AI customer's intent from the scenario goal of its instruction."""

    if goal.startswith("Book a "):
        return "booking"

    if goal.startswith("Ask how much"):
        return "price"

    if goal.startswith(("Ask to talk to a human", "Report an emergency")):
        return "human"

    return "other"


def read_reply_language(context: str) -> str | None:
    """The language the platform read the customer in (its context line)."""

    found: list[str] = REPLY_LANGUAGE_PATTERN.findall(context)
    if not found or found[-1] not in ASSISTANT_TEXTS:
        return None

    return found[-1]


def detect_language(text: str) -> str:
    """ka, ru or en by the script the customer wrote in."""

    if any("\u10a0" <= character <= "\u10ff" for character in text):
        return "ka"

    if any("\u0400" <= character <= "\u04ff" for character in text):
        return "ru"

    return "en"
