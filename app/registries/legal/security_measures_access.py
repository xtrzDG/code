"""
DPA section 9, first part: who can sign in and open a Client's data, and how
it is protected in transit and at rest. Each measure names the code that
implements it (tests/legal checks the paths exist).
"""

from app.registries.legal.subprocessor_texts import texts
from app.schemas.dto.security_measures import SecurityMeasure
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.legal.constrained_strings import (
    RepositoryPath,
    SecurityMeasureKey,
)

# The first DPA version whose section 9 is generated from this registry.
GENERATED_SECTION_FROM: DpaDocumentVersion = DpaDocumentVersion("2026-10-06")


def paths(*values: str) -> list[RepositoryPath]:
    return [RepositoryPath(value) for value in values]


ACCESS_MEASURES: tuple[SecurityMeasure, ...] = (
    SecurityMeasure(
        key=SecurityMeasureKey("transport_encryption"),
        text=texts(
            "encryption of all traffic over the internet (TLS), with strict "
            "transport and security headers on the API and the cabinet",
            "шифрование всего трафика через интернет (TLS) со строгими "
            "заголовками безопасности в API и кабинете",
            "ინტერნეტით გადაცემული მთელი ტრაფიკის დაშიფვრა (TLS), API-სა და "
            "კაბინეტში უსაფრთხოების მკაცრი სათაურებით",
        ),
        implemented_by=paths(
            "app/gateways/http/middleware/security_headers_middleware.py",
            "web/src/server/contentSecurityPolicy.ts",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("encryption_at_rest"),
        text=texts(
            "encryption at rest of the access tokens of the Client's channels "
            "and of authenticator secrets, under keys that are rotated; call "
            "recordings, media files and full data exports are encrypted with "
            "a key of their business",
            "шифрование при хранении токенов доступа к каналам Клиента и "
            "секретов приложений-аутентификаторов ключами, которые меняются; "
            "записи звонков, файлы и полные выгрузки данных шифруются ключом "
            "своего бизнеса",
            "კლიენტის არხების წვდომის ტოკენებისა და ავთენტიკატორის "
            "საიდუმლოებების დაშიფვრა შენახვისას, ცვალებადი გასაღებებით; "
            "ზარების ჩანაწერები, ფაილები და მონაცემების სრული ექსპორტი "
            "იშიფრება მისი ბიზნესის გასაღებით",
        ),
        implemented_by=paths(
            "app/adapters/security/secret_cipher_adapter.py",
            "app/utilities/security/key_ring.py",
            "app/utilities/security/recording_encryption.py",
            "app/utilities/security/media_encryption.py",
            "app/utilities/security/export_encryption.py",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("tenant_isolation"),
        text=texts(
            "separation of every Client's data in the database (row-level "
            "security keyed by the business), in addition to checks in the "
            "application",
            "разделение данных каждого Клиента в базе данных (защита на уровне "
            "строк по бизнесу) в дополнение к проверкам в приложении",
            "თითოეული კლიენტის მონაცემების გამიჯვნა მონაცემთა ბაზაში (სტრიქონის "
            "დონის დაცვა ბიზნესის მიხედვით) აპლიკაციის შემოწმებების გარდა",
        ),
        implemented_by=paths(
            "migrations/0001_document_collections.sql",
            "app/utilities/storage/storage_scope_context.py",
            "app/use_cases/authorize_business_access_use_case.py",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("one_time_code_sign_in"),
        text=texts(
            "sign-in with one-time codes, with limits per destination, per "
            "network and per attempt and a bot check for unusual requests",
            "вход по одноразовым кодам с ограничениями на адрес, сеть и число "
            "попыток и проверкой на ботов при необычных запросах",
            "შესვლა ერთჯერადი კოდებით, მისამართის, ქსელისა და მცდელობების "
            "შეზღუდვებით და ბოტების შემოწმებით უჩვეულო მოთხოვნებისას",
        ),
        implemented_by=paths(
            "app/use_cases/users/otp_login/login_code_limits.py",
            "app/use_cases/users/otp_login/login_check_limits.py",
            "app/use_cases/users/otp_login/login_risk_signals.py",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("two_factor_sign_in"),
        text=texts(
            "two-factor sign-in with an authenticator app and single-use "
            "recovery codes: required for the Provider's administrators and, "
            "at the Client's choice, for its team; removing or replacing a "
            "factor takes effect on every signed-in device",
            "двухфакторный вход с приложением-аутентификатором и одноразовыми "
            "кодами восстановления: обязателен для администраторов Поставщика "
            "и, по выбору Клиента, для его команды; удаление или замена "
            "фактора действует на всех устройствах, где выполнен вход",
            "ორფაქტორიანი შესვლა ავთენტიკატორის აპლიკაციითა და ერთჯერადი "
            "აღდგენის კოდებით: სავალდებულოა მომწოდებლის ადმინისტრატორებისთვის "
            "და, კლიენტის არჩევით, მისი გუნდისთვის; ფაქტორის წაშლა ან შეცვლა "
            "მოქმედებს ყველა მოწყობილობაზე, სადაც შესვლა შესრულებულია",
        ),
        implemented_by=paths(
            "app/utilities/security/totp_codes.py",
            "app/utilities/security/recovery_codes.py",
            "app/utilities/security/two_factor_policy.py",
            "app/use_cases/shared/session_sweeps.py",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("recent_confirmation"),
        text=texts(
            "a fresh confirmation, at most 10 minutes old, before sensitive "
            "actions: data exports and erasure, changes of the team, the "
            "channels and the privacy settings",
            "свежее подтверждение (не старше 10 минут) перед важными "
            "действиями: выгрузкой и удалением данных, изменением команды, "
            "каналов и настроек приватности",
            "ახალი დადასტურება (არაუმეტეს 10 წუთისა) მნიშვნელოვანი "
            "მოქმედებების წინ: მონაცემების ექსპორტი და წაშლა, გუნდის, არხებისა "
            "და კონფიდენციალურობის პარამეტრების შეცვლა",
        ),
        implemented_by=paths("app/utilities/security/require_recent_authentication.py"),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("device_sessions"),
        text=texts(
            "sessions that end after a period without use and at an absolute "
            "limit, a list of signed-in devices that can be ended remotely, "
            "and a notice of every sign-in from a new device",
            "сеансы, которые завершаются после периода без использования и по "
            "абсолютному сроку, список устройств со входом с возможностью "
            "завершить их удалённо и уведомление о каждом входе с нового "
            "устройства",
            "სესიები, რომლებიც სრულდება გამოუყენებლობის პერიოდის შემდეგ და "
            "აბსოლუტური ვადით, მოწყობილობების სია, რომელთა დასრულებაც "
            "დისტანციურად შეიძლება, და შეტყობინება ახალი მოწყობილობიდან "
            "ყოველი შესვლის შესახებ",
        ),
        implemented_by=paths(
            "app/utilities/security/session_expiry.py",
            "app/use_cases/users/sessions",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("roles"),
        text=texts(
            "roles of owner and staff; billing, settings and requests about "
            "customers' data only for owners",
            "роли владельца и сотрудника; оплата, настройки и запросы по данным "
            "клиентов — только для владельцев",
            "მფლობელისა და თანამშრომლის როლები; გადახდა, პარამეტრები და "
            "მომხმარებლების მონაცემებზე მოთხოვნები — მხოლოდ მფლობელებისთვის",
        ),
        implemented_by=paths("app/use_cases/authorize_business_access_use_case.py"),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("support_access"),
        text=texts(
            "access by the Provider's support only with a stated reason, for "
            "at most 60 minutes and read-only unless the Client allows changes; "
            "the Client sees it in the cabinet and it is recorded in the audit "
            "log",
            "доступ поддержки Поставщика только с указанной причиной, не "
            "дольше 60 минут и только на чтение, если Клиент не разрешил "
            "изменения; Клиент видит его в кабинете, и он записывается в "
            "журнал аудита",
            "მომწოდებლის მხარდაჭერის წვდომა მხოლოდ მითითებული მიზეზით, "
            "არაუმეტეს 60 წუთისა და მხოლოდ წასაკითხად, თუ კლიენტმა ცვლილებები "
            "არ დაუშვა; კლიენტი მას კაბინეტში ხედავს და ის აუდიტის ჟურნალში "
            "იწერება",
        ),
        implemented_by=paths(
            "app/use_cases/authorize_support_access_use_case.py",
            "app/utilities/security/support_refusals.py",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
)
