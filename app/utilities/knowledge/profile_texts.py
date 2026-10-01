"""Owner-facing texts of the profile wizard and the "what to add" list.

English and Russian are mandatory, Georgian is provided; other languages
fall back to the base language and then to English. Gap texts may contain
{label}, {noun}, {question} and {count} placeholders.
"""

from app.schemas.constants.niches import ProfileWizardStep
from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.dto.localization import LocalizedText
from app.utilities.knowledge.localized_texts import build_localized_text

WIZARD_STEP_ORDER: tuple[ProfileWizardStep, ...] = (
    ProfileWizardStep.NICHE_AND_LANGUAGES,
    ProfileWizardStep.CONTACTS_AND_HOURS,
    ProfileWizardStep.OFFER,
    ProfileWizardStep.BOOKING_RULES,
    ProfileWizardStep.FAQ_AND_HANDOFF,
    ProfileWizardStep.CHANNELS,
)

WIZARD_STEP_TITLES: dict[ProfileWizardStep, LocalizedText] = {
    ProfileWizardStep.NICHE_AND_LANGUAGES: build_localized_text(
        en="Niche and languages",
        ru="Ниша и языки",
        ka="ნიშა და ენები",
    ),
    ProfileWizardStep.CONTACTS_AND_HOURS: build_localized_text(
        en="Contacts and hours",
        ru="Контакты и часы",
        ka="კონტაქტები და საათები",
    ),
    ProfileWizardStep.OFFER: build_localized_text(
        en="What you sell",
        ru="Что продаём",
        ka="რას ყიდით",
    ),
    ProfileWizardStep.BOOKING_RULES: build_localized_text(
        en="Booking rules",
        ru="Правила брони",
        ka="ჯავშნის წესები",
    ),
    ProfileWizardStep.FAQ_AND_HANDOFF: build_localized_text(
        en="Questions and handoff",
        ru="Вопросы и передача человеку",
        ka="კითხვები და გადაცემა",
    ),
    ProfileWizardStep.CHANNELS: build_localized_text(
        en="Channels and links",
        ru="Каналы и ссылки",
        ka="არხები და ბმულები",
    ),
}

WIZARD_STEP_DESCRIPTIONS: dict[ProfileWizardStep, LocalizedText] = {
    ProfileWizardStep.NICHE_AND_LANGUAGES: build_localized_text(
        en="Your business type, the languages the assistant speaks and a few "
        "questions about your niche.",
        ru="Тип бизнеса, языки помощника и несколько вопросов по нише.",
        ka="ბიზნესის ტიპი, ასისტენტის ენები და რამდენიმე კითხვა ნიშის შესახებ.",
    ),
    ProfileWizardStep.CONTACTS_AND_HOURS: build_localized_text(
        en="Address, maps link, phones and opening hours.",
        ru="Адрес, ссылка на карту, телефоны и часы работы.",
        ka="მისამართი, რუკის ბმული, ტელეფონები და სამუშაო საათები.",
    ),
    ProfileWizardStep.OFFER: build_localized_text(
        en="Menu, services, rooms or packages with prices in your currency.",
        ru="Меню, услуги, номера или пакеты с ценами в вашей валюте.",
        ka="მენიუ, მომსახურება, ოთახები ან პაკეტები ფასებით თქვენს ვალუტაში.",
    ),
    ProfileWizardStep.BOOKING_RULES: build_localized_text(
        en="Slot length, maximum party size, minimum notice, deposit and cancellation.",
        ru="Длительность слота, максимум гостей, минимальный срок, депозит и отмена.",
        ka="სლოტის ხანგრძლივობა, სტუმრების მაქსიმუმი, მინიმალური ვადა, "
        "დეპოზიტი და გაუქმება.",
    ),
    ProfileWizardStep.FAQ_AND_HANDOFF: build_localized_text(
        en="Frequent questions, when to pass a conversation to a person, what is "
        "forbidden and the tone.",
        ru="Частые вопросы, когда передавать разговор человеку, запреты и тон.",
        ka="ხშირი კითხვები, როდის გადაეცეს საუბარი ადამიანს, აკრძალვები და ტონი.",
    ),
    ProfileWizardStep.CHANNELS: build_localized_text(
        en="Links the assistant may send and the call recording notice. Connect "
        "the channels themselves in the Channels section.",
        ru="Ссылки, которые может отправлять помощник, и предупреждение о записи "
        "звонка. Сами каналы подключаются в разделе «Каналы».",
        ka="ბმულები, რომლებსაც ასისტენტი გაგზავნის, და ზარის ჩაწერის "
        "გაფრთხილება. თავად არხები დაუკავშირეთ განყოფილებაში „არხები“.",
    ),
}

GAP_TEXTS: dict[ProfileGapKind, LocalizedText] = {
    ProfileGapKind.MISSING_REQUIRED_ANSWER: build_localized_text(
        en="Answer the question “{label}”.",
        ru="Ответьте на вопрос «{label}».",
        ka="უპასუხეთ კითხვას „{label}“.",
    ),
    ProfileGapKind.NO_OPENING_HOURS: build_localized_text(
        en="Add your opening hours.",
        ru="Укажите часы работы.",
        ka="მიუთითეთ სამუშაო საათები.",
    ),
    ProfileGapKind.NO_ADDRESS: build_localized_text(
        en="Add the address and a maps link.",
        ru="Укажите адрес и ссылку на карту.",
        ka="მიუთითეთ მისამართი და რუკის ბმული.",
    ),
    ProfileGapKind.NO_HANDOFF_CONTACT: build_localized_text(
        en="Add a manager contact: handoffs, new bookings and requests are sent "
        "to it, so the assistant can pass difficult cases to a person.",
        ru="Добавьте контакт менеджера: туда приходят передачи, новые брони и "
        "заявки, чтобы помощник мог передавать сложные случаи человеку.",
        ka="დაამატეთ მენეჯერის კონტაქტი: მასზე მოდის გადაცემები, ახალი "
        "ჯავშნები და მოთხოვნები, რათა ასისტენტმა რთული შემთხვევები ადამიანს "
        "გადასცეს.",
    ),
    ProfileGapKind.NO_BOOKING_RULES: build_localized_text(
        en="Set the booking rules: slot length, maximum party size and minimum notice.",
        ru="Задайте правила брони: длительность слота, максимум гостей и "
        "минимальный срок.",
        ka="დააყენეთ ჯავშნის წესები: სლოტის ხანგრძლივობა, სტუმრების "
        "მაქსიმალური რაოდენობა და მინიმალური ვადა.",
    ),
    ProfileGapKind.NO_RESOURCES: build_localized_text(
        en="Add what customers book ({noun}).",
        ru="Добавьте, что бронируют клиенты ({noun}).",
        ka="დაამატეთ, რას ჯავშნიან კლიენტები ({noun}).",
    ),
    ProfileGapKind.NO_PRICED_ITEMS: build_localized_text(
        en="Add your prices: the assistant names only prices from the price list.",
        ru="Добавьте цены: помощник называет только цены из прайса.",
        ka="დაამატეთ ფასები: ასისტენტი ასახელებს მხოლოდ ფასებს ფასების სიიდან.",
    ),
    ProfileGapKind.NO_FAQ: build_localized_text(
        en="Add frequent questions and answers.",
        ru="Добавьте частые вопросы и ответы.",
        ka="დაამატეთ ხშირად დასმული კითხვები და პასუხები.",
    ),
    ProfileGapKind.UNANSWERED_QUESTION: build_localized_text(
        en="Unanswered customer question: “{question}” (times asked: {count}). "
        "Add an answer.",
        ru="Вопрос клиентов без ответа: «{question}» (сколько раз задан: "
        "{count}). Добавьте ответ.",
        ka="კლიენტების პასუხგაუცემელი კითხვა: „{question}“ (დაისვა {count}-ჯერ). "
        "დაამატეთ პასუხი.",
    ),
}
