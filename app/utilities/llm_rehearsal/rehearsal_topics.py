"""
The rehearsal's grouping of what customers ask about (LLM_PROVIDER=scripted,
and the demo data): each item goes to the first topic one of its keywords
names (bookings, prices, opening hours, the address, the menu and
services), else to other questions; labels in the requested language
(English for one without labels here).
"""

import json
import re
from collections.abc import Sequence
from enum import StrEnum

LABEL_LANGUAGE_LINE: re.Pattern[str] = re.compile(r"^Label language: (\S+)$", re.M)
ITEM_LINE: re.Pattern[str] = re.compile(r"^([CQ]\d+): (.*)$", re.M)
FALLBACK_LANGUAGE: str = "en"


class RehearsalTopic(StrEnum):
    BOOKING = "booking"
    PRICES = "prices"
    HOURS = "hours"
    PLACE = "place"
    OFFER = "offer"
    OTHER = "other"


KEYWORDS: dict[RehearsalTopic, tuple[str, ...]] = {
    RehearsalTopic.BOOKING: (
        "book", "reserv", "table for", "appointment", "termin", "брон",
        "столик", "запис", "დაჯავშ", "მაგიდ", "ჩაწერ",
    ),
    RehearsalTopic.PRICES: (
        "price", "cost", "how much", "preis", "kostet", "цен", "стоит",
        "сколько", "ფას", "ღირ", "რა ღირს",
    ),
    RehearsalTopic.HOURS: (
        "open", "hour", "close", "öffnungs", "geöffnet", "работа", "часы",
        "открыт", "закрыт", "საათ", "ღია", "დაკეტ",
    ),
    RehearsalTopic.PLACE: (
        "where", "address", "parking", "adresse", "parken", "адрес", "где",
        "парков", "მისამართ", "სად", "პარკინგ",
    ),
    RehearsalTopic.OFFER: (
        "menu", "vegan", "dish", "service", "speisekarte", "angebot", "меню",
        "блюд", "веган", "услуг", "მენიუ", "კერძ", "მომსახურ",
    ),
}  # fmt: skip
LABELS: dict[str, dict[RehearsalTopic, str]] = {
    "en": {
        RehearsalTopic.BOOKING: "Booking",
        RehearsalTopic.PRICES: "Prices",
        RehearsalTopic.HOURS: "Opening hours",
        RehearsalTopic.PLACE: "Address and parking",
        RehearsalTopic.OFFER: "Menu and services",
        RehearsalTopic.OTHER: "Other questions",
    },
    "ru": {
        RehearsalTopic.BOOKING: "Бронирование",
        RehearsalTopic.PRICES: "Цены",
        RehearsalTopic.HOURS: "Часы работы",
        RehearsalTopic.PLACE: "Адрес и парковка",
        RehearsalTopic.OFFER: "Меню и услуги",
        RehearsalTopic.OTHER: "Другие вопросы",
    },
    "ka": {
        RehearsalTopic.BOOKING: "ჯავშანი",
        RehearsalTopic.PRICES: "ფასები",
        RehearsalTopic.HOURS: "სამუშაო საათები",
        RehearsalTopic.PLACE: "მისამართი და პარკინგი",
        RehearsalTopic.OFFER: "მენიუ და მომსახურება",
        RehearsalTopic.OTHER: "სხვა კითხვები",
    },
    "de": {
        RehearsalTopic.BOOKING: "Buchung",
        RehearsalTopic.PRICES: "Preise",
        RehearsalTopic.HOURS: "Öffnungszeiten",
        RehearsalTopic.PLACE: "Adresse und Parken",
        RehearsalTopic.OFFER: "Angebot und Leistungen",
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
