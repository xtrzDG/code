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
}

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


def detect_language(text: str) -> str:
    """ka, ru or en by the script the customer wrote in."""

    if any("\u10a0" <= character <= "\u10ff" for character in text):
        return "ka"

    if any("\u0400" <= character <= "\u04ff" for character in text):
        return "ru"

    return "en"
