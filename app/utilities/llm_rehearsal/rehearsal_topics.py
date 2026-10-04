"""
The rehearsal's grouping of what customers ask about (LLM_PROVIDER=scripted,
and the demo data): each item goes to the first topic one of its keywords
names (celebrations, bookings, opening hours, prices, the address, the
menu and services, complaints), else to other questions; labels in the
requested language (English for one without labels here).
"""

import json
import re
from collections.abc import Sequence
from enum import StrEnum

LABEL_LANGUAGE_LINE: re.Pattern[str] = re.compile(r"^Label language: (\S+)$", re.M)
ITEM_LINE: re.Pattern[str] = re.compile(r"^([CQ]\d+): (.*)$", re.M)
FALLBACK_LANGUAGE: str = "en"


class RehearsalTopic(StrEnum):
    EVENTS = "events"
    BOOKING = "booking"
    HOURS = "hours"
    PRICES = "prices"
    PLACE = "place"
    OFFER = "offer"
    COMPLAINT = "complaint"
    OTHER = "other"


# Checked in this order: a birthday dinner is an event before a booking, a
# complaint about a dish is a complaint, and "во сколько" (at what time)
# is about the hours before "стоит" prices.
KEYWORDS: dict[RehearsalTopic, tuple[str, ...]] = {
    RehearsalTopic.EVENTS: (
        "birthday", "party", "group of", "wedding", "corporate", "event",
        "день рожд", "корпоратив", "банкет", "свадьб", "праздн", "ქორწილ",
        "დაბადების", "ბანკეტ", "დარბაზ",
    ),
    RehearsalTopic.COMPLAINT: (
        "disappoint", "waited", "complain", "turned out", "unzufrieden",
        "разочарован", "ждали", "жалоб", "პასუხი არ", "წუთია",
    ),
    RehearsalTopic.BOOKING: (
        "book", "reserv", "table", "appointment", "termin", "adults",
        "people", "guests", "cancel", "free on", "absag", "zeit für", "брон",
        "столик", "стол на", "запис", "прийти", "на двоих", "на троих",
        "отмен", "დაჯავშ", "ჯავშ", "მაგიდ", "ჩაწერ", "კაცზე", "კაცისთვის",
        "მოსვლა", "გაუქმ",
    ),
    RehearsalTopic.HOURS: (
        "open", "hour", "close", "what time", "öffnungs", "geöffnet",
        "работа", "часы", "во сколько", "открыт", "открыва", "закрыт",
        "საათ", "ღია", "იხსნებ", "დაკეტ",
    ),
    RehearsalTopic.PRICES: (
        "price", "cost", "how much", "discount", "corkage", "fee", "preis",
        "kostet", "rabatt", "цен", "стоит", "почём", "скидк", "ფას", "ღირ",
    ),
    RehearsalTopic.PLACE: (
        "where", "address", "parking", "adresse", "parken", "адрес", "где",
        "парков", "მისამართ", "სად", "პარკინგ",
    ),
    RehearsalTopic.OFFER: (
        "menu", "vegan", "vegetarian", "dish", "wine", "khachapuri",
        "music", "service", "manicure", "lash", "haircut", "colour",
        "balayage", "schnitt", "haare", "maniküre", "speisekarte", "angebot",
        "меню", "блюд", "веган", "вегетариан", "хинкали", "музык", "услуг",
        "стрижк", "маникюр", "окраш", "მენიუ", "კერძ", "ხაჭაპურ", "უგლუტენ",
        "მუსიკ", "მიტან", "მომსახურ",
    ),
}  # fmt: skip
LABELS: dict[str, dict[RehearsalTopic, str]] = {
    "en": {
        RehearsalTopic.EVENTS: "Celebrations and events",
        RehearsalTopic.BOOKING: "Booking",
        RehearsalTopic.PRICES: "Prices",
        RehearsalTopic.HOURS: "Opening hours",
        RehearsalTopic.PLACE: "Address and parking",
        RehearsalTopic.OFFER: "Menu and services",
        RehearsalTopic.COMPLAINT: "Complaints",
        RehearsalTopic.OTHER: "Other questions",
    },
    "ru": {
        RehearsalTopic.EVENTS: "Праздники и банкеты",
        RehearsalTopic.BOOKING: "Бронирование",
        RehearsalTopic.PRICES: "Цены",
        RehearsalTopic.HOURS: "Часы работы",
        RehearsalTopic.PLACE: "Адрес и парковка",
        RehearsalTopic.OFFER: "Меню и услуги",
        RehearsalTopic.COMPLAINT: "Жалобы",
        RehearsalTopic.OTHER: "Другие вопросы",
    },
    "ka": {
        RehearsalTopic.EVENTS: "ზეიმები და ბანკეტები",
        RehearsalTopic.BOOKING: "ჯავშანი",
        RehearsalTopic.PRICES: "ფასები",
        RehearsalTopic.HOURS: "სამუშაო საათები",
        RehearsalTopic.PLACE: "მისამართი და პარკინგი",
        RehearsalTopic.OFFER: "მენიუ და მომსახურება",
        RehearsalTopic.COMPLAINT: "საჩივრები",
        RehearsalTopic.OTHER: "სხვა კითხვები",
    },
    "de": {
        RehearsalTopic.EVENTS: "Feiern und Veranstaltungen",
        RehearsalTopic.BOOKING: "Buchung",
        RehearsalTopic.PRICES: "Preise",
        RehearsalTopic.HOURS: "Öffnungszeiten",
        RehearsalTopic.PLACE: "Adresse und Parken",
        RehearsalTopic.OFFER: "Angebot und Leistungen",
        RehearsalTopic.COMPLAINT: "Beschwerden",
        RehearsalTopic.OTHER: "Andere Fragen",
    },
}


def classify_topic(text: str) -> RehearsalTopic:
    lowered: str = text.casefold()
    for topic, words in KEYWORDS.items():
        if any(word in lowered for word in words):
            return topic

    return RehearsalTopic.OTHER


def topic_label(topic: RehearsalTopic, language: str) -> str:
    base: str = language.split("-")[0].lower()
    return LABELS.get(base, LABELS[FALLBACK_LANGUAGE])[topic]


def group_items(
    items: Sequence[tuple[str, str]], language: str
) -> list[tuple[str, list[str]]]:
    """(label, item names) per topic, in the order the topics first appear."""

    grouped: dict[RehearsalTopic, list[str]] = {}
    for name, text in items:
        grouped.setdefault(classify_topic(text), []).append(name)

    return [(topic_label(topic, language), names) for topic, names in grouped.items()]


def rehearse_topics(request_text: str) -> str:
    """The rehearsal's answer to a grouping request, as the model answers."""

    match: re.Match[str] | None = LABEL_LANGUAGE_LINE.search(request_text)
    language: str = FALLBACK_LANGUAGE if match is None else match.group(1)
    items: list[tuple[str, str]] = ITEM_LINE.findall(request_text)
    topics = group_items(items, language)
    return json.dumps(
        {"topics": [{"label": label, "items": names} for label, names in topics]},
        ensure_ascii=False,
    )
