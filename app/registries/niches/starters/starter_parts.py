"""
Building blocks of the niche starter answers: texts come as (English,
Russian, Georgian) triples, times as hours and minutes of the day.
"""

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.setup.starter_catalog import (
    StarterBookingDefaults,
    StarterFaqDefinition,
    StarterOfferDefinition,
    StarterOpening,
    StarterResourceDefaults,
)
from app.schemas.typings.bookings.constrained_integers import (
    MinNoticeMinutes,
    PartySize,
    ResourceCapacity,
    ResourceUnitCount,
    SlotDurationMinutes,
)
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.knowledge.constrained_integers import ServiceDurationMinutes
from app.schemas.typings.setup.constrained_strings import StarterEntryKey
from app.utilities.knowledge.localized_texts import build_localized_text

type Texts = tuple[str, str, str]
type DayHours = tuple[int, int]

MINUTES_PER_HOUR: int = 60


def text(texts: Texts) -> LocalizedText:
    """An owner-facing text in English, Russian and Georgian."""

    english, russian, georgian = texts
    return build_localized_text(en=english, ru=russian, ka=georgian)


def at(hour: int, minute: int = 0) -> int:
    """Minute of the day of a wall-clock time (24:00 is 1440)."""

    return hour * MINUTES_PER_HOUR + minute


def opening(workday: DayHours, weekend: DayHours | None) -> StarterOpening:
    """Hours on working days and on the country's weekend (None: closed)."""

    return StarterOpening(
        workday_opens_at=OpeningMinuteOfDay(workday[0]),
        workday_closes_at=ClosingMinuteOfDay(workday[1]),
        weekend_opens_at=None if weekend is None else OpeningMinuteOfDay(weekend[0]),
        weekend_closes_at=(
            None if weekend is None else ClosingMinuteOfDay(weekend[1])
        ),
    )


def booking(
    slot_minutes: int | None,
    max_party_size: int,
    min_notice_minutes: int,
    cancellation_policy: Texts,
) -> StarterBookingDefaults:
    """Typical booking rules; `slot_minutes` None for nights."""

    return StarterBookingDefaults(
        slot_minutes=None if slot_minutes is None else SlotDurationMinutes(slot_minutes),
        max_party_size=PartySize(max_party_size),
        min_notice_minutes=MinNoticeMinutes(min_notice_minutes),
        cancellation_policies=text(cancellation_policy),
    )


def resource(names: Texts, capacity: int, unit_count: int) -> StarterResourceDefaults:
    """The first bookable thing of a niche."""

    return StarterResourceDefaults(
        names=text(names),
        capacity=ResourceCapacity(capacity),
        unit_count=ResourceUnitCount(unit_count),
    )


def ready_faq(key: str, question: Texts, answer: Texts) -> StarterFaqDefinition:
    """A frequent question with an answer that holds for the whole niche."""

    return StarterFaqDefinition(
        key=StarterEntryKey(key),
        questions=text(question),
        answers=text(answer),
    )


def open_faq(key: str, question: Texts) -> StarterFaqDefinition:
    """A frequent question only the owner can answer."""

    return StarterFaqDefinition(key=StarterEntryKey(key), questions=text(question))


def offer(
    key: str,
    kind: KnowledgeItemKind,
    titles: Texts,
    duration_minutes: int | None = None,
) -> StarterOfferDefinition:
    """An example of what the niche sells (never priced)."""

    return StarterOfferDefinition(
        key=StarterEntryKey(key),
        kind=kind,
        titles=text(titles),
        duration_minutes=(
            None
            if duration_minutes is None
            else ServiceDurationMinutes(duration_minutes)
        ),
    )


# Shared texts.
CHANGE_RESERVATION = ready_faq(
    "change_booking",
    (
        "Can I change or cancel my booking?",
        "Можно ли перенести или отменить бронь?",
        "შეიძლება ჯავშნის გადატანა ან გაუქმება?",
    ),
    (
        "Yes. Write here which booking you want to change, and I will move or "
        "cancel it.",
        "Да. Напишите здесь, какую бронь нужно изменить, — я перенесу или отменю её.",
        "დიახ. დაწერეთ აქ, რომელი ჯავშნის შეცვლა გსურთ — გადავიტან ან გავაუქმებ.",
    ),
)
CHANGE_APPOINTMENT = ready_faq(
    "change_booking",
    (
        "Can I move or cancel my appointment?",
        "Можно ли перенести или отменить запись?",
        "შეიძლება ჩაწერის გადატანა ან გაუქმება?",
    ),
    (
        "Yes. Write here which appointment you want to change, and I will move or "
        "cancel it.",
        "Да. Напишите здесь, какую запись нужно изменить, — я перенесу или отменю её.",
        "დიახ. დაწერეთ აქ, რომელი ჩაწერის შეცვლა გსურთ — გადავიტან ან გავაუქმებ.",
    ),
)
NOTICE_THREE_HOURS: Texts = (
    "Please let us know at least 3 hours in advance if you cannot come.",
    "Если не сможете прийти, предупредите нас, пожалуйста, хотя бы за 3 часа.",
    "თუ ვერ მოხვალთ, გთხოვთ, გაგვაფრთხილოთ მინიმუმ 3 საათით ადრე.",
)
NOTICE_TWELVE_HOURS: Texts = (
    "Please let us know at least 12 hours in advance if you need to move the "
    "appointment.",
    "Если нужно перенести запись, предупредите нас, пожалуйста, хотя бы за 12 часов.",
    "თუ ჩაწერის გადატანა გჭირდებათ, გთხოვთ, გაგვაფრთხილოთ მინიმუმ 12 საათით ადრე.",
)

CARD_PAYMENT = open_faq(
    "card_payment",
    (
        "Can I pay by card?",
        "Можно ли оплатить картой?",
        "შეიძლება ბარათით გადახდა?",
    ),
)
