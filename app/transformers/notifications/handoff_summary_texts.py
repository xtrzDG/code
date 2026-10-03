"""
Localized texts of the handoffs the platform creates itself (a reply that
failed, figures the guard held back, a reply that never arrived, erased
data): what happened, then the quoted words. The cabinet keeps the same
texts in its `handoffs.summaryCodes` dictionary.
"""

from collections.abc import Mapping

from app.schemas.constants.handoffs import HandoffSummaryCode
from app.schemas.dto.localization import LocalizedText
from app.transformers.notifications.message_rendering import localized

# What happened, for a code that lists no flagged values.
SUMMARY_TEXTS: Mapping[HandoffSummaryCode, LocalizedText] = {
    HandoffSummaryCode.MODEL_DECLINED: localized(
        en="The assistant would not answer this message.",
        ru="Помощник не стал отвечать на это сообщение.",
        ka="ასისტენტმა ამ შეტყობინებას პასუხი არ გასცა.",
    ),
    HandoffSummaryCode.MODEL_UNAVAILABLE: localized(
        en="The assistant was briefly unavailable and could not answer.",
        ru="Помощник был временно недоступен и не смог ответить.",
        ka="ასისტენტი დროებით მიუწვდომელი იყო და პასუხი ვერ გასცა.",
    ),
    HandoffSummaryCode.ANSWER_UNFINISHED: localized(
        en="The assistant could not finish its answer.",
        ru="Помощник не смог закончить ответ.",
        ka="ასისტენტმა პასუხის დასრულება ვერ მოახერხა.",
    ),
    HandoffSummaryCode.UNVERIFIED_VALUES: localized(
        en="The assistant held back an answer with figures that are not in "
        "your business details.",
        ru="Помощник не отправил ответ: в нём были цифры, которых нет в данных "
        "бизнеса.",
        ka="ასისტენტმა პასუხი არ გაგზავნა: მასში იყო ციფრები, რომლებიც "
        "ბიზნესის მონაცემებში არ არის.",
    ),
    HandoffSummaryCode.CALL_BOOKING_UNVERIFIED_VALUES: localized(
        en="On the call the assistant named figures that are not in your "
        "business details. Check the booking from this call against the "
        "transcript.",
        ru="Во время звонка помощник назвал цифры, которых нет в данных "
        "бизнеса. Сверьте бронь из этого звонка с расшифровкой.",
        ka="ზარისას ასისტენტმა დაასახელა ციფრები, რომლებიც ბიზნესის "
        "მონაცემებში არ არის. შეადარეთ ამ ზარის ჯავშანი ზარის ტრანსკრიპტს.",
    ),
    HandoffSummaryCode.CALL_REQUEST_UNVERIFIED_VALUES: localized(
        en="On the call the assistant named figures that are not in your "
        "business details. Check the request from this call against the "
        "transcript.",
        ru="Во время звонка помощник назвал цифры, которых нет в данных "
        "бизнеса. Сверьте заявку из этого звонка с расшифровкой.",
        ka="ზარისას ასისტენტმა დაასახელა ციფრები, რომლებიც ბიზნესის "
        "მონაცემებში არ არის. შეადარეთ ამ ზარის მოთხოვნა ზარის ტრანსკრიპტს.",
    ),
    HandoffSummaryCode.REPLY_UNDELIVERED: localized(
        en="The assistant's reply did not reach the customer. Contact them "
        "another way.",
        ru="Ответ помощника не дошёл до клиента. Свяжитесь с ним другим способом.",
        ka="ასისტენტის პასუხი კლიენტამდე ვერ მივიდა. დაუკავშირდით მას სხვა გზით.",
    ),
    HandoffSummaryCode.DATA_ERASED: localized(
        en="Details erased at the customer's request.",
        ru="Данные удалены по просьбе клиента.",
        ka="მონაცემები წაიშალა კლიენტის თხოვნით.",
    ),
}
# What happened, for a code with flagged values: `{values}` lists them.
SUMMARY_TEXTS_WITH_VALUES: Mapping[HandoffSummaryCode, LocalizedText] = {
    HandoffSummaryCode.UNVERIFIED_VALUES: localized(
        en="The assistant held back an answer with figures that are not in "
        "your business details ({values}).",
        ru="Помощник не отправил ответ: в нём были цифры, которых нет в данных "
        "бизнеса ({values}).",
        ka="ასისტენტმა პასუხი არ გაგზავნა: მასში იყო ციფრები, რომლებიც "
        "ბიზნესის მონაცემებში არ არის ({values}).",
    ),
    HandoffSummaryCode.CALL_BOOKING_UNVERIFIED_VALUES: localized(
        en="On the call the assistant named figures that are not in your "
        "business details ({values}). Check the booking from this call "
        "against the transcript.",
        ru="Во время звонка помощник назвал цифры, которых нет в данных "
        "бизнеса ({values}). Сверьте бронь из этого звонка с расшифровкой.",
        ka="ზარისას ასისტენტმა დაასახელა ციფრები, რომლებიც ბიზნესის "
        "მონაცემებში არ არის ({values}). შეადარეთ ამ ზარის ჯავშანი ზარის "
        "ტრანსკრიპტს.",
    ),
    HandoffSummaryCode.CALL_REQUEST_UNVERIFIED_VALUES: localized(
        en="On the call the assistant named figures that are not in your "
        "business details ({values}). Check the request from this call "
        "against the transcript.",
        ru="Во время звонка помощник назвал цифры, которых нет в данных "
        "бизнеса ({values}). Сверьте заявку из этого звонка с расшифровкой.",
        ka="ზარისას ასისტენტმა დაასახელა ციფრები, რომლებიც ბიზნესის "
        "მონაცემებში არ არის ({values}). შეადარეთ ამ ზარის მოთხოვნა ზარის "
        "ტრანსკრიპტს.",
    ),
}
# The quoted words: the reply that did not arrive, else the customer's.
QUOTED_REPLY: LocalizedText = localized(
    en="The reply: “{text}”",
    ru="Ответ: «{text}»",
    ka="პასუხი: „{text}“",
)
QUOTED_CUSTOMER_MESSAGE: LocalizedText = localized(
    en="The customer's message: “{text}”",
    ru="Сообщение клиента: «{text}»",
    ka="კლიენტის შეტყობინება: „{text}“",
)
VALUE_SEPARATOR: str = ", "
