"""
Call forwarding texts and codes (concept section 6: "в кабинете — инструкция
по переадресации для Magti, Silknet и Cellfie").

Codes are the GSM supplementary-service codes for conditional forwarding:
**61* no answer, **67* busy, **62* unreachable, ##002# cancels all forwarding.
Magti publishes exactly these (*61, *67, *62, concept "Стек"). Texts exist in
English, Russian and Georgian; other languages fall back to English. Text
placeholders: {number}, {no_answer_code}, {busy_code}, {unreachable_code},
{cancel_code}.
"""

from app.schemas.constants.localization import CallForwardingCondition
from app.schemas.dto.catalog import CallForwardingCodeTemplate, CarrierForwardingGuide
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import (
    CallForwardingDialCodeTemplate,
    CountryCode,
)
from app.schemas.typings.localization.strings import CarrierName
from app.utilities.localization.localized_texts import build_localized_text

GSM_CODE_TEMPLATES: tuple[CallForwardingCodeTemplate, ...] = (
    CallForwardingCodeTemplate(
        condition=CallForwardingCondition.NO_ANSWER,
        dial_code_template=CallForwardingDialCodeTemplate("**61*{number}#"),
        descriptions=build_localized_text(
            en="Forward calls you do not answer.",
            ru="Переадресация звонков, на которые вы не ответили.",
            ka="იმ ზარების გადამისამართება, რომლებსაც არ უპასუხეთ.",
        ),
    ),
    CallForwardingCodeTemplate(
        condition=CallForwardingCondition.BUSY,
        dial_code_template=CallForwardingDialCodeTemplate("**67*{number}#"),
        descriptions=build_localized_text(
            en="Forward calls while the line is busy.",
            ru="Переадресация звонков, когда линия занята.",
            ka="ზარების გადამისამართება, როცა ხაზი დაკავებულია.",
        ),
    ),
    CallForwardingCodeTemplate(
        condition=CallForwardingCondition.UNREACHABLE,
        dial_code_template=CallForwardingDialCodeTemplate("**62*{number}#"),
        descriptions=build_localized_text(
            en="Forward calls while the phone is off or out of coverage.",
            ru="Переадресация звонков, когда телефон выключен или вне сети.",
            ka=(
                "ზარების გადამისამართება, როცა ტელეფონი გამორთულია ან "
                "დაფარვის ზონის გარეთაა."
            ),
        ),
    ),
    CallForwardingCodeTemplate(
        condition=CallForwardingCondition.CANCEL_ALL,
        dial_code_template=CallForwardingDialCodeTemplate("##002#"),
        descriptions=build_localized_text(
            en="Switch all call forwarding off.",
            ru="Отключить всю переадресацию.",
            ka="ყველა გადამისამართების გაუქმება.",
        ),
    ),
)

FORWARDING_STEPS: tuple[LocalizedText, ...] = (
    build_localized_text(
        en="Take the phone with the SIM card whose number your guests call.",
        ru="Возьмите телефон с SIM-картой, на номер которой звонят ваши гости.",
        ka="აიღეთ ტელეფონი იმ SIM ბარათით, რომლის ნომერზეც რეკავენ თქვენი სტუმრები.",
    ),
    build_localized_text(
        en=(
            "Dial {no_answer_code} and press call: calls you do not answer go "
            "to the assistant at {number}."
        ),
        ru=(
            "Наберите {no_answer_code} и нажмите вызов: звонки, на которые вы "
            "не ответили, уйдут ассистенту на номер {number}."
        ),
        ka=(
            "აკრიფეთ {no_answer_code} და დააჭირეთ დარეკვას: ზარები, რომლებსაც "
            "არ უპასუხებთ, გადავა ასისტენტთან ნომერზე {number}."
        ),
    ),
    build_localized_text(
        en=(
            "Dial {busy_code} and press call: calls while the line is busy go "
            "to the assistant."
        ),
        ru=(
            "Наберите {busy_code} и нажмите вызов: звонки, пока линия занята, "
            "уйдут ассистенту."
        ),
        ka=(
            "აკრიფეთ {busy_code} და დააჭირეთ დარეკვას: ზარები, როცა ხაზი "
            "დაკავებულია, გადავა ასისტენტთან."
        ),
    ),
    build_localized_text(
        en=(
            "Dial {unreachable_code} and press call: calls while the phone is "
            "off or out of coverage go to the assistant."
        ),
        ru=(
            "Наберите {unreachable_code} и нажмите вызов: звонки, когда телефон "
            "выключен или вне сети, уйдут ассистенту."
        ),
        ka=(
            "აკრიფეთ {unreachable_code} და დააჭირეთ დარეკვას: ზარები, როცა "
            "ტელეფონი გამორთულია ან დაფარვის ზონის გარეთაა, გადავა ასისტენტთან."
        ),
    ),
    build_localized_text(
        en="After each code wait for the carrier's confirmation on the screen.",
        ru="После каждого кода дождитесь подтверждения оператора на экране.",
        ka="ყოველი კოდის შემდეგ დაელოდეთ ოპერატორის დადასტურებას ეკრანზე.",
    ),
    build_localized_text(
        en=(
            "Check it: call your number from another phone and do not answer. "
            "The assistant should pick up."
        ),
        ru=(
            "Проверьте: позвоните на свой номер с другого телефона и не берите "
            "трубку. Должен ответить ассистент."
        ),
        ka=(
            "შეამოწმეთ: დარეკეთ თქვენს ნომერზე სხვა ტელეფონიდან და არ "
            "უპასუხოთ. ასისტენტმა უნდა უპასუხოს."
        ),
    ),
)

FORWARDING_NOTES: tuple[LocalizedText, ...] = (
    build_localized_text(
        en=(
            "These are standard GSM codes. Some carriers use other codes or "
            "switch forwarding on only in their app or through support; if a "
            "code does not work, ask your carrier."
        ),
        ru=(
            "Это стандартные коды GSM. Некоторые операторы используют другие "
            "коды или включают переадресацию только в приложении или через "
            "поддержку; если код не сработал, спросите оператора."
        ),
        ka=(
            "ეს სტანდარტული GSM კოდებია. ზოგი ოპერატორი სხვა კოდებს იყენებს ან "
            "გადამისამართებას მხოლოდ აპლიკაციით ან მხარდაჭერის მეშვეობით "
            "რთავს; თუ კოდი არ მუშაობს, მიმართეთ ოპერატორს."
        ),
    ),
    build_localized_text(
        en=(
            "Forward only unanswered, busy and unreachable calls, never every "
            "call: your staff keep answering first."
        ),
        ru=(
            "Переадресуйте только неотвеченные, занятые и недоступные звонки, "
            "а не все: сотрудники по-прежнему отвечают первыми."
        ),
        ka=(
            "გადაამისამართეთ მხოლოდ უპასუხო, დაკავებული და მიუწვდომელი ზარები "
            "და არა ყველა: თქვენი თანამშრომლები კვლავ პირველები პასუხობენ."
        ),
    ),
    build_localized_text(
        en="Your carrier bills forwarded calls under your own tariff.",
        ru="Переадресованные звонки оператор тарифицирует по вашему тарифу.",
        ka="გადამისამართებულ ზარებს ოპერატორი თქვენი ტარიფით გიანგარიშებთ.",
    ),
    build_localized_text(
        en="To switch forwarding off, dial {cancel_code}.",
        ru="Чтобы отключить переадресацию, наберите {cancel_code}.",
        ka="გადამისამართების გასათიშად აკრიფეთ {cancel_code}.",
    ),
)


def build_unconfirmed_carrier_note(carrier_name: str) -> LocalizedText:
    return build_localized_text(
        en=(
            f"Standard GSM codes, not yet confirmed with {carrier_name}: if a "
            f"code fails, ask {carrier_name} support."
        ),
        ru=(
            f"Стандартные коды GSM, с {carrier_name} ещё не подтверждены: если "
            f"код не сработал, обратитесь в поддержку {carrier_name}."
        ),
        ka=(
            f"სტანდარტული GSM კოდები, {carrier_name}-თან ჯერ არ არის "
            f"დადასტურებული: თუ კოდი არ იმუშავებს, მიმართეთ {carrier_name}-ის "
            "მხარდაჭერას."
        ),
    )


CARRIER_GUIDES_BY_COUNTRY: dict[CountryCode, tuple[CarrierForwardingGuide, ...]] = {
    CountryCode("GE"): (
        CarrierForwardingGuide(
            carrier_name=CarrierName("Magti"),
            code_templates=list(GSM_CODE_TEMPLATES),
            notes=build_localized_text(
                en="Magti publishes these codes: *61 no answer, *67 busy, "
                "*62 unreachable.",
                ru="Эти коды публикует Magti: *61 — нет ответа, *67 — занято, "
                "*62 — вне сети.",
                ka="ამ კოდებს Magti აქვეყნებს: *61 — არ პასუხობს, *67 — "
                "დაკავებულია, *62 — მიუწვდომელია.",
            ),
        ),
        CarrierForwardingGuide(
            carrier_name=CarrierName("Silknet"),
            code_templates=list(GSM_CODE_TEMPLATES),
            notes=build_unconfirmed_carrier_note("Silknet"),
        ),
        CarrierForwardingGuide(
            carrier_name=CarrierName("Cellfie"),
            code_templates=list(GSM_CODE_TEMPLATES),
            notes=build_unconfirmed_carrier_note("Cellfie"),
        ),
    ),
}
