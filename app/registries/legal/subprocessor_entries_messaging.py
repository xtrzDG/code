"""
The sub-processors that carry messages and calls: the phone line, the
messengers, SMS, e-mail and the browsers' push services.
"""

from app.registries.legal.subprocessor_texts import (
    ORIGINAL_LIST_DATE,
    key,
    modules,
    texts,
)
from app.schemas.dto.legal import SubprocessorEntry

MESSAGING_SUBPROCESSORS: tuple[SubprocessorEntry, ...] = (
    SubprocessorEntry(
        key=key("zadarma"),
        name=texts("Zadarma", "Zadarma", "Zadarma"),
        purpose=texts(
            "Phone numbers and call routing (SIP)",
            "Телефонные номера и маршрутизация звонков (SIP)",
            "ტელეფონის ნომრები და ზარების მარშრუტიზაცია (SIP)",
        ),
        personal_data=texts(
            "Caller and called numbers, call audio in transit",
            "Номера звонящего и вызываемого, аудио звонков при передаче",
            "აბონენტისა და გამოძახებული ნომრები, ზარის აუდიო გადაცემისას",
        ),
        location=texts(
            "[EU, to be confirmed]",
            "[ЕС, уточнить]",
            "[ევროკავშირი, დასაზუსტებელია]",
        ),
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("meta"),
        name=texts(
            "Meta Platforms Ireland (WhatsApp Business Platform, Instagram, Messenger)",
            "Meta Platforms Ireland (WhatsApp Business Platform, Instagram, Messenger)",
            "Meta Platforms Ireland (WhatsApp Business Platform, Instagram, Messenger)",
        ),
        purpose=texts(
            "Receiving and sending messages in these channels",
            "Приём и отправка сообщений в этих каналах",
            "ამ არხებში შეტყობინებების მიღება და გაგზავნა",
        ),
        personal_data=texts(
            "Messages, user identifiers, phone number (WhatsApp)",
            "Сообщения, идентификаторы пользователей, номер телефона (WhatsApp)",
            "შეტყობინებები, მომხმარებლის იდენტიფიკატორები, ტელეფონის ნომერი (WhatsApp)",
        ),
        location=texts(
            "EU and other locations under Meta's terms",
            "ЕС и другие места по условиям Meta",
            "ევროკავშირი და სხვა ადგილები Meta-ს პირობების მიხედვით",
        ),
        client_modules=modules("meta"),
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("telegram"),
        name=texts("Telegram", "Telegram", "Telegram"),
        purpose=texts(
            "The Telegram channel of the Client and staff notifications",
            "Канал Telegram Клиента и уведомления сотрудникам",
            "კლიენტის Telegram-არხი და თანამშრომელთა შეტყობინებები",
        ),
        personal_data=texts(
            "Messages, user identifiers",
            "Сообщения, идентификаторы пользователей",
            "შეტყობინებები, მომხმარებლის იდენტიფიკატორები",
        ),
        location=texts(
            "Outside the EEA [transfer mechanism to be confirmed]",
            "За пределами ЕЭЗ [механизм передачи уточнить]",
            "ევროპის ეკონომიკური ზონის გარეთ [გადაცემის მექანიზმი დასაზუსტებელია]",
        ),
        client_modules=modules("telegram"),
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("email"),
        name=texts(
            "E-mail provider (SMTP: [provider to be named, e.g. Mailgun EU, "
            "Postmark, Amazon SES])",
            "Почтовый сервис (SMTP: [назвать поставщика, например Mailgun EU, "
            "Postmark, Amazon SES])",
            "ელფოსტის სერვისი (SMTP: [მომწოდებელი დასასახელებელია, მაგალითად "
            "Mailgun EU, Postmark, Amazon SES])",
        ),
        purpose=texts(
            "Sign-in codes, staff notifications, digests and monthly reports by e-mail",
            "Коды входа, уведомления сотрудникам, сводки и ежемесячные отчёты по "
            "e-mail",
            "შესვლის კოდები, თანამშრომლების შეტყობინებები, შეჯამებები და "
            "ყოველთვიური ანგარიშები ელფოსტით",
        ),
        personal_data=texts(
            "E-mail addresses of cabinet users; notification contents (customer "
            "names, booking details, message excerpts)",
            "Адреса e-mail пользователей кабинета; содержание уведомлений (имена "
            "клиентов, данные броней, фрагменты сообщений)",
            "კაბინეტის მომხმარებლების ელფოსტის მისამართები; შეტყობინებების "
            "შინაარსი (მომხმარებლების სახელები, ჯავშნების მონაცემები, "
            "შეტყობინებების ნაწყვეტები)",
        ),
        location=texts(
            "[EU, to be confirmed]",
            "[ЕС, уточнить]",
            "[ევროკავშირი, დასაზუსტებელია]",
        ),
        client_modules=modules("email"),
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("twilio"),
        name=texts("Twilio", "Twilio", "Twilio"),
        purpose=texts(
            "Sign-in codes and staff notifications by SMS; a text message to a "
            "caller who could not get through, when the Client turns it on",
            "Коды входа и уведомления сотрудникам по SMS; SMS звонившему, который "
            "не дозвонился, если Клиент это включил",
            "შესვლის კოდები და თანამშრომლების შეტყობინებები SMS-ით; SMS "
            "დამრეკისთვის, რომელმაც ვერ დარეკა, თუ კლიენტმა ეს ჩართო",
        ),
        personal_data=texts(
            "Phone numbers, message contents",
            "Номера телефонов, текст сообщений",
            "ტელეფონის ნომრები, შეტყობინებების ტექსტი",
        ),
        location=texts(
            "[United States / Ireland; transfer mechanism to be confirmed]",
            "[США / Ирландия; механизм передачи уточнить]",
            "[აშშ / ირლანდია; გადაცემის მექანიზმი დასაზუსტებელია]",
        ),
        client_modules=modules("twilio"),
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("web_push"),
        name=texts(
            "Web Push services of the browsers (Google Firebase Cloud Messaging, "
            "Mozilla, Apple)",
            "Сервисы веб-push браузеров (Google Firebase Cloud Messaging, Mozilla, "
            "Apple)",
            "ბრაუზერების ვებ-push სერვისები (Google Firebase Cloud Messaging, "
            "Mozilla, Apple)",
        ),
        purpose=texts(
            "Push notifications to the devices of staff who turned them on",
            "Push-уведомления на устройства сотрудников, которые их включили",
            "push-შეტყობინებები იმ თანამშრომლების მოწყობილობებზე, რომლებმაც "
            "ისინი ჩართეს",
        ),
        personal_data=texts(
            "The device's push address and an end-to-end encrypted notification "
            "the service cannot read",
            "Push-адрес устройства и уведомление, зашифрованное сквозным "
            "шифрованием, которое сервис не может прочитать",
            "მოწყობილობის push მისამართი და ბოლომდე დაშიფრული შეტყობინება, "
            "რომელსაც სერვისი ვერ წაიკითხავს",
        ),
        location=texts(
            "[Outside the EEA, under each browser vendor's terms]",
            "[За пределами ЕЭЗ, на условиях производителя браузера]",
            "[ევროპის ეკონომიკური ზონის გარეთ, ბრაუზერის მწარმოებლის პირობებით]",
        ),
        client_modules=modules("webpush"),
        added_on=ORIGINAL_LIST_DATE,
    ),
)
