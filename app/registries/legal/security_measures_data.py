"""
DPA section 9, second part: what happens to the Client's data once it is in
the service: the audit log, exports, retention, the checks of the
assistant's replies, the processors' purposes, backups and the Provider's
own practice. Each measure names what implements it.
"""

from app.registries.legal.security_measures_access import (
    GENERATED_SECTION_FROM,
    paths,
)
from app.registries.legal.subprocessor_texts import texts
from app.schemas.dto.security_measures import SecurityMeasure
from app.schemas.typings.legal.constrained_strings import SecurityMeasureKey

DATA_MEASURES: tuple[SecurityMeasure, ...] = (
    SecurityMeasure(
        key=SecurityMeasureKey("audit_log"),
        text=texts(
            "an audit log of operations on personal data (views, exports, "
            "erasures, changes of the team, support access), shown to the "
            "Client in the cabinet",
            "журнал аудита операций с персональными данными (просмотры, "
            "выгрузки, удаления, изменения команды, доступ поддержки), "
            "доступный Клиенту в кабинете",
            "პერსონალურ მონაცემებზე ოპერაციების აუდიტის ჟურნალი (ნახვები, "
            "ექსპორტი, წაშლა, გუნდის ცვლილებები, მხარდაჭერის წვდომა), "
            "რომელიც კლიენტს კაბინეტში ეჩვენება",
        ),
        implemented_by=paths(
            "app/repositories/compliance_repositories.py",
            "app/use_cases/compliance/list_audit_log_use_case.py",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("export_links"),
        text=texts(
            "a full export of the Client's data opens only through a one-time "
            "link that is valid for 10 minutes, works only for the owner who "
            "asked for it, allows at most three downloads of an export, and "
            "every download is announced to all owners",
            "полная выгрузка данных Клиента открывается только по одноразовой "
            "ссылке, которая действует 10 минут, работает только для "
            "запросившего её владельца, допускает не больше трёх скачиваний "
            "одной выгрузки, и о каждом скачивании узнают все владельцы",
            "კლიენტის მონაცემების სრული ექსპორტი იხსნება მხოლოდ ერთჯერადი "
            "ბმულით, რომელიც 10 წუთი მოქმედებს, მუშაობს მხოლოდ მომთხოვნი "
            "მფლობელისთვის, ერთ ექსპორტზე არაუმეტეს სამ ჩამოტვირთვას უშვებს "
            "და ყოველი ჩამოტვირთვის შესახებ ყველა მფლობელი იგებს",
        ),
        implemented_by=paths(
            "app/use_cases/exports/create_export_download_link_use_case.py",
            "app/use_cases/exports/download_business_export_use_case.py",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("retention"),
        text=texts(
            "automatic deletion of conversations, records of language model "
            "calls and call recordings after the periods the Client sets",
            "автоматическое удаление разговоров, записей вызовов языковой "
            "модели и записей звонков после сроков, которые задаёт Клиент",
            "საუბრების, ენობრივი მოდელის გამოძახებების ჩანაწერებისა და ზარების "
            "ჩანაწერების ავტომატური წაშლა კლიენტის მიერ დადგენილი ვადების "
            "შემდეგ",
        ),
        implemented_by=paths(
            "app/use_cases/compliance/retention/purge_expired_personal_data_use_case.py",
            "app/use_cases/compliance/purge_expired_recordings_use_case.py",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("reply_checks"),
        text=texts(
            "checks of the assistant's replies before they are sent: no "
            "contact details of another customer, prices and promises only "
            "from the Client's facts, text from outside marked as untrusted; "
            "test conversations kept apart from real ones",
            "проверки ответов помощника перед отправкой: никаких контактов "
            "другого клиента, цены и обещания — только из фактов Клиента, "
            "текст извне помечен как недоверенный; тестовые разговоры отделены "
            "от настоящих",
            "ასისტენტის პასუხების შემოწმება გაგზავნამდე: სხვა მომხმარებლის "
            "საკონტაქტო მონაცემები არ იგზავნება, ფასები და დაპირებები მხოლოდ "
            "კლიენტის ფაქტებიდან, გარედან მიღებული ტექსტი მონიშნულია როგორც "
            "არასანდო; სატესტო საუბრები რეალურისგან გამიჯნულია",
        ),
        implemented_by=paths(
            "app/utilities/reply_guard/contact_details.py",
            "app/utilities/reply_guard/claim_candidates.py",
            "app/utilities/conversations/untrusted_text.py",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("processor_purposes"),
        text=texts(
            "personal data reaches a sub-processor only for the purposes "
            "section 8 names for it; the service does not start when its "
            "settings would send data elsewhere",
            "персональные данные попадают к субобработчику только для целей, "
            "указанных для него в разделе 8; сервис не запускается, если его "
            "настройки отправили бы данные иначе",
            "პერსონალური მონაცემები ქვე-უფლებამოსილ პირთან მხოლოდ მე-8 ნაწილში "
            "მისთვის მითითებული მიზნებისთვის ხვდება; სერვისი არ ირთვება, თუ "
            "მისი პარამეტრები მონაცემებს სხვაგან გაგზავნიდა",
        ),
        implemented_by=paths(
            "app/registries/legal/processor_use_catalog.py",
            "app/utilities/legal/processor_coverage.py",
            "app/gateways/startup_checks.py",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("backups"),
        text=texts(
            "daily encrypted backups of the database kept in the EU (30 daily "
            "and 12 monthly copies), with regular restore drills",
            "ежедневные зашифрованные резервные копии базы данных в ЕС (30 "
            "ежедневных и 12 ежемесячных копий) с регулярными проверками "
            "восстановления",
            "მონაცემთა ბაზის ყოველდღიური დაშიფრული სარეზერვო ასლები "
            "ევროკავშირში (30 ყოველდღიური და 12 ყოველთვიური ასლი) აღდგენის "
            "რეგულარული შემოწმებით",
        ),
        implemented_by=paths(
            "app/adapters/backup/age_backup_cipher_adapter.py",
            "app/utilities/backups/backup_retention.py",
            ".github/workflows/restore-drill.yml",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
    SecurityMeasure(
        key=SecurityMeasureKey("operations"),
        text=texts(
            "confidentiality obligations and least-privilege access for the "
            "Provider's personnel with a quarterly access review, error "
            "monitoring, and regular updates and automated security scans of "
            "the software",
            "обязательства о конфиденциальности и минимально необходимый "
            "доступ для персонала Поставщика с ежеквартальной проверкой "
            "доступов, мониторинг ошибок, регулярные обновления и "
            "автоматические проверки безопасности программного обеспечения",
            "კონფიდენციალურობის ვალდებულებები და მინიმალური აუცილებელი წვდომა "
            "მომწოდებლის პერსონალისთვის წვდომების კვარტალური შემოწმებით, "
            "შეცდომების მონიტორინგი, პროგრამული უზრუნველყოფის რეგულარული "
            "განახლება და უსაფრთხოების ავტომატური შემოწმებები",
        ),
        implemented_by=paths(
            "docs/security/access-review.md",
            "SECURITY.md",
            ".github/workflows/codeql.yml",
        ),
        listed_from=GENERATED_SECTION_FROM,
    ),
)
