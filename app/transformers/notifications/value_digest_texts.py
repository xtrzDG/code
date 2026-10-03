"""
Localized templates of the owners' value digests (daily, weekly) and
monthly reports: what the assistant did and is worth, compared with the
period before, the link to the report and how to stop receiving it.
Counts follow "label: value" so no sentence needs plural forms.
"""

from collections.abc import Mapping

from app.schemas.constants.value import ValueBasis, ValueReportKind
from app.schemas.dto.localization import LocalizedText
from app.transformers.notifications.message_rendering import localized

TITLES: Mapping[ValueReportKind, LocalizedText] = {
    ValueReportKind.DAILY: localized(
        en="Your assistant yesterday · {business}",
        ru="Ваш помощник вчера · {business}",
        ka="თქვენი ასისტენტი გუშინ · {business}",
    ),
    ValueReportKind.WEEKLY: localized(
        en="Your assistant last week · {business}",
        ru="Ваш помощник за неделю · {business}",
        ka="თქვენი ასისტენტი გასულ კვირას · {business}",
    ),
    ValueReportKind.MONTHLY: localized(
        en="Monthly report, {month} · {business}",
        ru="Отчёт за месяц: {month} · {business}",
        ka="თვის ანგარიში: {month} · {business}",
    ),
}
EARNINGS: Mapping[ValueBasis, LocalizedText] = {
    ValueBasis.BOOKINGS: localized(
        en="Bookings by the assistant: {count}",
        ru="Брони через помощника: {count}",
        ka="ასისტენტის ჯავშნები: {count}",
    ),
    ValueBasis.REQUESTS: localized(
        en="Orders and requests taken: {count}",
        ru="Принятые заказы и заявки: {count}",
        ka="მიღებული შეკვეთები და მოთხოვნები: {count}",
    ),
}
MONEY: LocalizedText = localized(en="≈ {money}", ru="≈ {money}", ka="≈ {money}")
CHANGE_AGAINST: Mapping[ValueReportKind, LocalizedText] = {
    ValueReportKind.DAILY: localized(
        en="({change} vs the day before)",
        ru="({change} к предыдущему дню)",
        ka="({change} წინა დღესთან შედარებით)",
    ),
    ValueReportKind.WEEKLY: localized(
        en="({change} vs the week before)",
        ru="({change} к предыдущей неделе)",
        ka="({change} წინა კვირასთან შედარებით)",
    ),
    ValueReportKind.MONTHLY: localized(
        en="({change} vs the month before)",
        ru="({change} к предыдущему месяцу)",
        ka="({change} წინა თვესთან შედარებით)",
    ),
}
AFTER_HOURS: LocalizedText = localized(
    en="Conversations after hours: {count} (of {total})",
    ru="Обращения в нерабочее время: {count} (всего {total})",
    ka="საუბრები არასამუშაო საათებში: {count} ({total}-დან)",
)
TIME_SAVED: LocalizedText = localized(
    en="Staff time saved: about {time}",
    ru="Сэкономлено времени сотрудников: около {time}",
    ka="დაზოგილი სამუშაო დრო: დაახლოებით {time}",
)
HOURS: LocalizedText = localized(en="{count} h", ru="{count} ч", ka="{count} სთ")
MINUTES: LocalizedText = localized(en="{count} min", ru="{count} мин", ka="{count} წთ")
OTHER_COUNTS: Mapping[ValueBasis, LocalizedText] = {
    ValueBasis.BOOKINGS: localized(
        en="Conversations: {conversations} · Requests: {requests} · "
        "Needed a person: {handoffs}",
        ru="Обращения: {conversations} · Заявки: {requests} · "
        "Нужен человек: {handoffs}",
        ka="საუბრები: {conversations} · მოთხოვნები: {requests} · "
        "ადამიანის დახმარება: {handoffs}",
    ),
    ValueBasis.REQUESTS: localized(
        en="Conversations: {conversations} · Needed a person: {handoffs}",
        ru="Обращения: {conversations} · Нужен человек: {handoffs}",
        ka="საუბრები: {conversations} · ადამიანის დახმარება: {handoffs}",
    ),
}
NO_CHECK_HINT: LocalizedText = localized(
    en="Add your average check in the cabinet to see this in money.",
    ru="Укажите средний чек в кабинете, чтобы видеть это в деньгах.",
    ka="მიუთითეთ საშუალო ჩეკი კაბინეტში, რომ ეს თანხაში დაინახოთ.",
)
TYPICAL_CHECK_HINT: LocalizedText = localized(
    en="The amount uses a typical check of {check}; set your own in the cabinet.",
    ru="Сумма посчитана по типичному чеку {check}; укажите свой в кабинете.",
    ka="თანხა ტიპური ჩეკით ({check}) არის გამოთვლილი; მიუთითეთ თქვენი კაბინეტში.",
)
LINK_LINE: LocalizedText = localized(
    en="Open the report: {link}",
    ru="Открыть отчёт: {link}",
    ka="ანგარიშის გახსნა: {link}",
)
OPT_OUT: LocalizedText = localized(
    en="You get this summary as an owner of {business}. To stop it, open the "
    "report and turn it off under “Your summaries”.",
    ru="Вы получаете эту сводку как владелец «{business}». Чтобы отписаться, "
    "откройте отчёт и выключите её в блоке «Ваши сводки».",
    ka="ამ შეჯამებას იღებთ, როგორც „{business}“-ის მფლობელი. გამოსართავად "
    "გახსენით ანგარიში და გამორთეთ ის ბლოკში „თქვენი შეჯამებები“.",
)
