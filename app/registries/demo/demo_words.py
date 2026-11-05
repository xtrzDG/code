"""
Words customers use for days, so demo texts match the dates the tools saw:
"сегодня в 20:00", "ხვალ 13:00-ზე", "on Friday".
"""

from typed_time_provider import Microseconds

from app.registries.demo.demo_clock import DemoClock

TODAY_AND_TOMORROW: dict[str, tuple[str, str]] = {
    "ka": ("დღეს", "ხვალ"),
    "ru": ("сегодня", "завтра"),
    "en": ("today", "tomorrow"),
    "he": ("היום", "מחר"),
    "ar": ("اليوم", "غدًا"),
    "de": ("heute", "morgen"),
}
# "On <weekday>", Monday first.
ON_WEEKDAY: dict[str, tuple[str, ...]] = {
    "ka": (
        "ორშაბათს",
        "სამშაბათს",
        "ოთხშაბათს",
        "ხუთშაბათს",
        "პარასკევს",
        "შაბათს",
        "კვირას",
    ),
    "ru": (
        "в понедельник",
        "во вторник",
        "в среду",
        "в четверг",
        "в пятницу",
        "в субботу",
        "в воскресенье",
    ),
    "en": (
        "on Monday",
        "on Tuesday",
        "on Wednesday",
        "on Thursday",
        "on Friday",
        "on Saturday",
        "on Sunday",
    ),
    "he": (
        "ביום שני",
        "ביום שלישי",
        "ביום רביעי",
        "ביום חמישי",
        "ביום שישי",
        "בשבת",
        "ביום ראשון",
    ),
    "ar": (
        "يوم الاثنين",
        "يوم الثلاثاء",
        "يوم الأربعاء",
        "يوم الخميس",
        "يوم الجمعة",
        "يوم السبت",
        "يوم الأحد",
    ),
    "de": (
        "am Montag",
        "am Dienstag",
        "am Mittwoch",
        "am Donnerstag",
        "am Freitag",
        "am Samstag",
        "am Sonntag",
    ),
}


def day_word(
    clock: DemoClock,
    moment: Microseconds,
    language: str,
    said_at: Microseconds | None = None,
) -> str:
    """
    How a customer writing at `said_at` (default: now) names the day of
    `moment`: today, tomorrow or the weekday.
    """

    days_ahead: int = clock.days_from_today(moment) - (
        0 if said_at is None else clock.days_from_today(said_at)
    )
    if days_ahead in (0, 1):
        return TODAY_AND_TOMORROW[language][days_ahead]

    return ON_WEEKDAY[language][clock.weekday_index(moment)]
