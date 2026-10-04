"""Owner-facing texts of the guided setup in English, Russian and Georgian."""

from app.schemas.constants.setup import SetupActionTarget, SetupStepCode
from app.schemas.dto.localization import LocalizedText
from app.utilities.knowledge.localized_texts import build_localized_text

STEP_TITLES: dict[SetupStepCode, LocalizedText] = {
    SetupStepCode.BUSINESS: build_localized_text(
        en="Your business", ru="Ваш бизнес", ka="თქვენი ბიზნესი"
    ),
    SetupStepCode.OFFER: build_localized_text(
        en="What you offer", ru="Что вы предлагаете", ka="რას გთავაზობთ"
    ),
    SetupStepCode.HOURS_AND_BOOKINGS: build_localized_text(
        en="Hours and bookings",
        ru="Часы работы и запись",
        ka="სამუშაო საათები და ჯავშნები",
    ),
    SetupStepCode.STAFF_CONTACT: build_localized_text(
        en="Who gets the requests",
        ru="Кто получает заявки",
        ka="ვინ იღებს მოთხოვნებს",
    ),
    SetupStepCode.CHANNELS: build_localized_text(
        en="Where customers write",
        ru="Где пишут клиенты",
        ka="სად წერენ კლიენტები",
    ),
    SetupStepCode.TEST: build_localized_text(
        en="Try your assistant",
        ru="Попробуйте помощника",
        ka="გამოსცადეთ ასისტენტი",
    ),
    SetupStepCode.LAUNCH: build_localized_text(en="Go live", ru="Запуск", ka="გაშვება"),
    SetupStepCode.PHONE_TEST: build_localized_text(
        en="Try it from your phone",
        ru="Проверьте с телефона",
        ka="შეამოწმეთ ტელეფონიდან",
    ),
    SetupStepCode.SECOND_CHANNEL: build_localized_text(
        en="Add a second channel",
        ru="Подключите второй канал",
        ka="დაამატეთ მეორე არხი",
    ),
    SetupStepCode.SHARE: build_localized_text(
        en="Show customers where to write",
        ru="Покажите клиентам, куда писать",
        ka="აჩვენეთ კლიენტებს, სად მისწერონ",
    ),
}

STEP_DESCRIPTIONS: dict[SetupStepCode, LocalizedText] = {
    SetupStepCode.BUSINESS: build_localized_text(
        en="A few facts about your business that customers ask about first.",
        ru="Несколько фактов о бизнесе, о которых клиенты спрашивают первыми.",
        ka="რამდენიმე ფაქტი თქვენს ბიზნესზე, რასაც კლიენტები პირველ რიგში კითხულობენ.",
    ),
    SetupStepCode.OFFER: build_localized_text(
        en="Your services or menu with prices, so the assistant can quote them.",
        ru="Услуги или меню с ценами — помощник будет называть их клиентам.",
        ka="მომსახურება ან მენიუ ფასებით, რომ ასისტენტმა კლიენტებს უთხრას.",
    ),
    SetupStepCode.HOURS_AND_BOOKINGS: build_localized_text(
        en="When you are open and how customers book.",
        ru="Когда вы работаете и как клиенты записываются.",
        ka="როდის მუშაობთ და როგორ ჯავშნიან კლიენტები.",
    ),
    SetupStepCode.STAFF_CONTACT: build_localized_text(
        en="Who receives bookings, requests and questions the assistant passes on.",
        ru="Кто получает брони, заявки и вопросы, которые передаёт помощник.",
        ka="ვინ იღებს ჯავშნებს, მოთხოვნებსა და კითხვებს, რომლებსაც ასისტენტი "
        "გადასცემს.",
    ),
    SetupStepCode.CHANNELS: build_localized_text(
        en="Connect your website chat, Telegram, WhatsApp or Instagram.",
        ru="Подключите чат на сайте, Telegram, WhatsApp или Instagram.",
        ka="დააკავშირეთ საიტის ჩატი, Telegram, WhatsApp ან Instagram.",
    ),
    SetupStepCode.TEST: build_localized_text(
        en="Ask your assistant a few questions, as a customer would.",
        ru="Задайте помощнику пару вопросов, как это сделал бы клиент.",
        ka="დაუსვით ასისტენტს რამდენიმე კითხვა, როგორც კლიენტი დაუსვამდა.",
    ),
    SetupStepCode.LAUNCH: build_localized_text(
        en="We check the assistant and turn it on for your customers.",
        ru="Мы проверим помощника и включим его для ваших клиентов.",
        ka="შევამოწმებთ ასისტენტს და ჩავრთავთ თქვენი კლიენტებისთვის.",
    ),
    SetupStepCode.PHONE_TEST: build_localized_text(
        en="Scan the code and write to your assistant as a customer would.",
        ru="Отсканируйте код и напишите помощнику, как написал бы клиент.",
        ka="დაასკანერეთ კოდი და მისწერეთ ასისტენტს ისე, როგორც კლიენტი მისწერდა.",
    ),
    SetupStepCode.SECOND_CHANNEL: build_localized_text(
        en="Most customers write in WhatsApp, Telegram or Instagram: connect one.",
        ru="Большинство клиентов пишут в WhatsApp, Telegram или Instagram — "
        "подключите один из них.",
        ka="კლიენტების უმეტესობა WhatsApp-ში, Telegram-სა ან Instagram-ში "
        "წერს — დააკავშირეთ ერთ-ერთი.",
    ),
    SetupStepCode.SHARE: build_localized_text(
        en="Print the QR card for the counter or share the chat link.",
        ru="Распечатайте карточку с QR-кодом для стойки или поделитесь ссылкой на чат.",
        ka="ამობეჭდეთ QR-ბარათი დახლისთვის ან გააზიარეთ ჩატის ბმული.",
    ),
}

ACTION_LABELS: dict[SetupActionTarget, LocalizedText] = {
    SetupActionTarget.PROFILE: build_localized_text(
        en="Fill in", ru="Заполнить", ka="შევსება"
    ),
    SetupActionTarget.STAFF_CONTACTS: build_localized_text(
        en="Add a contact", ru="Добавить контакт", ka="კონტაქტის დამატება"
    ),
    SetupActionTarget.CHANNELS: build_localized_text(
        en="Connect a channel", ru="Подключить канал", ka="არხის დაკავშირება"
    ),
    SetupActionTarget.TEST_CHAT: build_localized_text(
        en="Open the test chat", ru="Открыть тестовый чат", ka="სატესტო ჩატის გახსნა"
    ),
    SetupActionTarget.AGREEMENT: build_localized_text(
        en="Accept the data agreement",
        ru="Принять соглашение о данных",
        ka="მონაცემთა შეთანხმების მიღება",
    ),
    SetupActionTarget.BILLING: build_localized_text(
        en="Choose a plan", ru="Выбрать тариф", ka="ტარიფის არჩევა"
    ),
    SetupActionTarget.CHECKS: build_localized_text(
        en="See the checks", ru="Посмотреть проверки", ka="შემოწმებების ნახვა"
    ),
    SetupActionTarget.APPLY_CHANGES: build_localized_text(
        en="Launch my assistant", ru="Запустить помощника", ka="ასისტენტის გაშვება"
    ),
    SetupActionTarget.OVERVIEW: build_localized_text(
        en="Open the overview", ru="Открыть обзор", ka="მიმოხილვის გახსნა"
    ),
    SetupActionTarget.PHONE_TEST: build_localized_text(
        en="Show the QR code", ru="Показать QR-код", ka="QR-კოდის ჩვენება"
    ),
    SetupActionTarget.SHARE: build_localized_text(
        en="Get the link and QR card",
        ru="Ссылка и карточка с QR",
        ka="ბმული და QR-ბარათი",
    ),
}

APPLY_CHANGES_AGAIN_LABEL: LocalizedText = build_localized_text(
    en="Apply changes", ru="Применить изменения", ka="ცვლილებების გამოყენება"
)
