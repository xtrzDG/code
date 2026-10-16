"""
The sub-processors the platform runs on: hosting, storage, monitoring, the
bot check, payments and the calendar a Client may connect.
"""

from app.registries.legal.subprocessor_texts import (
    ORIGINAL_LIST_DATE,
    key,
    modules,
    texts,
)
from app.schemas.dto.legal import SubprocessorEntry

PLATFORM_SUBPROCESSORS: tuple[SubprocessorEntry, ...] = (
    SubprocessorEntry(
        key=key("flitt"),
        name=texts("Flitt", "Flitt", "Flitt"),
        purpose=texts(
            "Payment of the Client's subscription",
            "Оплата подписки Клиента",
            "კლიენტის გამოწერის გადახდა",
        ),
        personal_data=texts(
            "Billing data of the Client (not of its customers)",
            "Платёжные данные Клиента (не его клиентов)",
            "კლიენტის (და არა მისი მომხმარებლების) გადახდის მონაცემები",
        ),
        location=texts(
            "[Georgia, to be confirmed]",
            "[Грузия, уточнить]",
            "[საქართველო, დასაზუსტებელია]",
        ),
        client_modules=modules("flitt"),
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("sentry"),
        name=texts("Sentry", "Sentry", "Sentry"),
        purpose=texts(
            "Monitoring of application errors",
            "Мониторинг ошибок приложения",
            "აპლიკაციის შეცდომების მონიტორინგი",
        ),
        personal_data=texts(
            "Technical error data, which may contain identifiers",
            "Технические данные ошибок, которые могут содержать идентификаторы",
            "შეცდომების ტექნიკური მონაცემები, რომლებიც შეიძლება იდენტიფიკატორებს "
            "შეიცავდეს",
        ),
        location=texts("EU region", "Регион ЕС", "ევროკავშირის რეგიონი"),
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("render"),
        name=texts("Render", "Render", "Render"),
        purpose=texts(
            "Hosting of the application, the database and the background worker",
            "Хостинг приложения, базы данных и фонового обработчика",
            "აპლიკაციის, მონაცემთა ბაზისა და ფონური დამმუშავებლის ჰოსტინგი",
        ),
        personal_data=texts(
            "All data of the service",
            "Все данные сервиса",
            "სერვისის ყველა მონაცემი",
        ),
        location=texts(
            "Frankfurt, Germany (EU)",
            "Франкфурт, Германия (ЕС)",
            "ფრანკფურტი, გერმანია (ევროკავშირი)",
        ),
        client_modules=modules("postgres"),
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("google_calendar"),
        name=texts(
            "Google (Google Calendar)",
            "Google (Google Calendar)",
            "Google (Google Calendar)",
        ),
        purpose=texts(
            "Only when the Client connects a calendar: copying bookings into it",
            "Только если Клиент подключил календарь: перенос броней в него",
            "მხოლოდ მაშინ, თუ კლიენტმა კალენდარი დააკავშირა: ჯავშნების გადატანა მასში",
        ),
        personal_data=texts(
            "Booking times, customer names and notes",
            "Время броней, имена клиентов и комментарии",
            "ჯავშნების დრო, მომხმარებლების სახელები და კომენტარები",
        ),
        location=texts(
            "[Google Ireland, to be confirmed]",
            "[Google Ireland, уточнить]",
            "[Google Ireland, დასაზუსტებელია]",
        ),
        client_modules=modules("google"),
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("cloudflare_turnstile"),
        name=texts(
            "Cloudflare (Turnstile)", "Cloudflare (Turnstile)", "Cloudflare (Turnstile)"
        ),
        purpose=texts(
            "Bot check when a sign-in code is requested for a new or busy destination",
            "Проверка на бота, когда код входа запрашивают на новый или слишком "
            "часто используемый адрес",
            "ბოტის შემოწმება, როცა შესვლის კოდს ახალ ან ზედმეტად ხშირად "
            "გამოყენებულ მისამართზე ითხოვენ",
        ),
        personal_data=texts(
            "IP address and browser signals of the cabinet user",
            "IP-адрес и признаки браузера пользователя кабинета",
            "კაბინეტის მომხმარებლის IP მისამართი და ბრაუზერის ნიშნები",
        ),
        location=texts(
            "[Global network; transfer mechanism to be confirmed]",
            "[Глобальная сеть; механизм передачи уточнить]",
            "[გლობალური ქსელი; გადაცემის მექანიზმი დასაზუსტებელია]",
        ),
        client_modules=modules("turnstile"),
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("object_storage"),
        name=texts(
            "EU object storage ([provider to be named], S3-compatible)",
            "Объектное хранилище в ЕС ([назвать поставщика], совместимое с S3)",
            "ობიექტური საცავი ევროკავშირში ([მომწოდებელი დასასახელებელია], "
            "S3-თან თავსებადი)",
        ),
        purpose=texts(
            "Call recordings, each encrypted with a key of its business; "
            "encrypted database backups (another provider)",
            "Записи звонков, каждая зашифрована ключом своего бизнеса; "
            "зашифрованные резервные копии базы данных (у другого поставщика)",
            "ზარების ჩანაწერები, თითოეული დაშიფრულია თავისი ბიზნესის გასაღებით; "
            "მონაცემთა ბაზის დაშიფრული სარეზერვო ასლები (სხვა მომწოდებელთან)",
        ),
        personal_data=texts(
            "Call audio; in backups, all data of the service, encrypted",
            "Аудио звонков; в резервных копиях — все данные сервиса в "
            "зашифрованном виде",
            "ზარების აუდიო; სარეზერვო ასლებში — სერვისის ყველა მონაცემი "
            "დაშიფრული სახით",
        ),
        location=texts("EU", "ЕС", "ევროკავშირი"),
        client_modules=modules("object_storage"),
        added_on=ORIGINAL_LIST_DATE,
    ),
)
