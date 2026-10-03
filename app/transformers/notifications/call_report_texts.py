"""
Localized templates of the staff texts about phone calls: the summary
after a call and the note about a caller who did not get through, with
their labels (how a call ended, why a caller did not get through, what
they were sent).
"""

from collections.abc import Mapping

from app.schemas.constants.calls import MissedCallReason, TextBackSkipReason
from app.schemas.constants.conversations import CallOutcome
from app.schemas.dto.localization import LocalizedText
from app.transformers.notifications.message_rendering import localized

CALL_SUMMARY_TITLE: LocalizedText = localized(
    en="Call summary · {business}",
    ru="Итог звонка · {business}",
    ka="ზარის შეჯამება · {business}",
)
MISSED_CALL_TITLE: LocalizedText = localized(
    en="Missed call · {business}",
    ru="Пропущенный звонок · {business}",
    ka="გამოტოვებული ზარი · {business}",
)
CALLER_LINE: LocalizedText = localized(
    en="Caller: {caller} · {when}",
    ru="Звонил: {caller} · {when}",
    ka="დამრეკი: {caller} · {when}",
)
HIDDEN_NUMBER: LocalizedText = localized(
    en="hidden number",
    ru="скрытый номер",
    ka="დამალული ნომერი",
)
RESULT_LINE: LocalizedText = localized(
    en="Result: {outcome}",
    ru="Итог: {outcome}",
    ka="შედეგი: {outcome}",
)
BOOKING_LINE: LocalizedText = localized(
    en="Booking: {when}, guests: {party}",
    ru="Бронь: {when}, гостей: {party}",
    ka="ჯავშანი: {when}, სტუმრები: {party}",
)
UNVERIFIED_LINE: LocalizedText = localized(
    en="Please check: the assistant mentioned {values}, which is not in your "
    "business data.",
    ru="Проверьте: помощник назвал {values}, а в данных бизнеса этого нет.",
    ka="გადაამოწმეთ: ასისტენტმა ახსენა {values}, თქვენი ბიზნესის მონაცემებში კი "
    "ეს არ არის.",
)
REASON_LINE: LocalizedText = localized(
    en="Why: {reason}",
    ru="Причина: {reason}",
    ka="მიზეზი: {reason}",
)
TEXTED_BY_WHATSAPP: LocalizedText = localized(
    en="We wrote to the caller on WhatsApp; their reply will come to your inbox.",
    ru="Мы написали звонившему в WhatsApp — его ответ придёт во входящие.",
    ka="დამრეკს WhatsApp-ში მივწერეთ — მისი პასუხი შემოსულებში მოვა.",
)
TEXTED_BY_SMS: LocalizedText = localized(
    en="We sent the caller an SMS. Please call them back if you can.",
    ru="Мы отправили звонившему SMS. Перезвоните, если можете.",
    ka="დამრეკს SMS გავუგზავნეთ. თუ შეგიძლიათ, გადაურეკეთ.",
)
NOT_TEXTED: LocalizedText = localized(
    en="We did not write to the caller ({why}). Please call them back if you can.",
    ru="Звонившему мы не написали ({why}). Перезвоните, если можете.",
    ka="დამრეკს არ მივწერეთ ({why}). თუ შეგიძლიათ, გადაურეკეთ.",
)
TEXT_BACK_FAILED: LocalizedText = localized(
    en="the message could not be sent",
    ru="сообщение не удалось отправить",
    ka="შეტყობინება ვერ გაიგზავნა",
)
MINUTES_AND_SECONDS: LocalizedText = localized(
    en="{minutes} min {seconds} s",
    ru="{minutes} мин {seconds} с",
    ka="{minutes} წთ {seconds} წმ",
)
SECONDS_ONLY: LocalizedText = localized(
    en="{seconds} s",
    ru="{seconds} с",
    ka="{seconds} წმ",
)
BRIEF_DETAIL: LocalizedText = localized(
    en="{outcome} · {duration}",
    ru="{outcome} · {duration}",
    ka="{outcome} · {duration}",
)
CALL_OUTCOME_LABELS: Mapping[str, LocalizedText] = {
    CallOutcome.BOOKING: localized(
        en="booking made", ru="оформлена бронь", ka="ჯავშანი გაკეთდა"
    ),
    CallOutcome.LEAD: localized(
        en="request taken", ru="принята заявка", ka="მოთხოვნა მიღებულია"
    ),
    CallOutcome.HANDOFF: localized(
        en="passed to a colleague",
        ru="передан сотруднику",
        ka="გადაეცა თანამშრომელს",
    ),
    CallOutcome.UNANSWERED_QUESTION: localized(
        en="a question without an answer",
        ru="вопрос без ответа",
        ka="უპასუხო კითხვა",
    ),
    CallOutcome.INFORMATION: localized(
        en="information given", ru="дана информация", ka="ინფორმაცია მიეწოდა"
    ),
    CallOutcome.ABANDONED: localized(
        en="the call ended early", ru="звонок прервался", ka="ზარი ადრე შეწყდა"
    ),
}
MISSED_REASON_LABELS: Mapping[str, LocalizedText] = {
    MissedCallReason.NO_ANSWER: localized(
        en="no one answered", ru="никто не ответил", ka="არავინ უპასუხა"
    ),
    MissedCallReason.BUSY: localized(
        en="the line was busy", ru="линия была занята", ka="ხაზი დაკავებული იყო"
    ),
    MissedCallReason.ABANDONED: localized(
        en="hung up before the assistant answered",
        ru="положил трубку до ответа помощника",
        ka="ასისტენტის პასუხამდე გათიშა",
    ),
    MissedCallReason.LINE_FAILED: localized(
        en="the call could not be put through",
        ru="звонок не удалось соединить",
        ka="ზარი ვერ დაკავშირდა",
    ),
    MissedCallReason.NOT_STARTED: localized(
        en="the assistant could not take the call",
        ru="помощник не смог принять звонок",
        ka="ასისტენტმა ზარი ვერ მიიღო",
    ),
    MissedCallReason.NO_SPEECH: localized(
        en="hung up without saying anything",
        ru="положил трубку, ничего не сказав",
        ka="ისე გათიშა, რომ არაფერი უთქვამს",
    ),
    MissedCallReason.TRANSFER_UNANSWERED: localized(
        en="asked for a person, and no one picked up",
        ru="просил соединить с сотрудником, но никто не взял трубку",
        ka="თანამშრომელთან დაკავშირება ითხოვა, მაგრამ არავინ უპასუხა",
    ),
}
SKIP_REASON_LABELS: Mapping[str, LocalizedText] = {
    TextBackSkipReason.TURNED_OFF: localized(
        en="messages after missed calls are off",
        ru="сообщения после пропущенных звонков выключены",
        ka="გამოტოვებული ზარების შემდეგ შეტყობინებები გამორთულია",
    ),
    TextBackSkipReason.OPTED_OUT: localized(
        en="they asked not to get messages",
        ru="клиент просил не присылать сообщения",
        ka="კლიენტმა შეტყობინებებზე უარი თქვა",
    ),
    TextBackSkipReason.ALREADY_TEXTED: localized(
        en="they already got a message today",
        ru="сегодня ему уже писали",
        ka="დღეს მას უკვე მივწერეთ",
    ),
    TextBackSkipReason.DAILY_LIMIT: localized(
        en="today's limit of messages is reached",
        ru="исчерпан дневной лимит сообщений",
        ka="დღიური ლიმიტი ამოიწურა",
    ),
    TextBackSkipReason.IN_CONVERSATION: localized(
        en="they are already writing to you",
        ru="он уже переписывается с вами",
        ka="ის უკვე გწერთ",
    ),
    TextBackSkipReason.NO_CHANNEL: localized(
        en="no WhatsApp template or SMS is set up",
        ru="не настроены шаблон WhatsApp и SMS",
        ka="WhatsApp-ის შაბლონი და SMS არ არის მორგებული",
    ),
    TextBackSkipReason.NOT_LIVE: localized(
        en="the assistant is not live",
        ru="помощник не запущен",
        ka="ასისტენტი არ არის გაშვებული",
    ),
    TextBackSkipReason.NO_CALLER_NUMBER: localized(
        en="the number was hidden", ru="номер был скрыт", ka="ნომერი დამალული იყო"
    ),
    TextBackSkipReason.TOO_LATE: localized(
        en="the call was too long ago",
        ru="звонок был слишком давно",
        ka="ზარი დიდი ხნის წინ იყო",
    ),
}
