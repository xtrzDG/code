"""
The headings of the exported tables in the owner's language, one list per
table in the order of its cells (the row readers of app/use_cases/exports
write cells in exactly this order).
"""

from app.schemas.constants.privacy import CsvExportKind
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text


def _title(en: str, ru: str, ka: str) -> LocalizedText:
    return build_localized_text(en=en, ru=ru, ka=ka)


CUSTOMER: LocalizedText = _title("Customer", "Клиент", "კლიენტი")
PHONE: LocalizedText = _title("Phone", "Телефон", "ტელეფონი")
CHANNEL: LocalizedText = _title("Channel", "Канал", "არხი")
STATUS: LocalizedText = _title("Status", "Статус", "სტატუსი")
CREATED: LocalizedText = _title("Created", "Создано", "შექმნილია")
TEST: LocalizedText = _title("Test chat", "Тестовый чат", "სატესტო ჩატი")
PARTY_SIZE: LocalizedText = _title("Guests", "Гостей", "სტუმრები")

CSV_COLUMNS: dict[CsvExportKind, tuple[LocalizedText, ...]] = {
    CsvExportKind.BOOKINGS: (
        _title("Booking ID", "ID брони", "ჯავშნის ID"),
        _title("Date", "Дата", "თარიღი"),
        _title("Time", "Время", "დრო"),
        _title("End date", "Дата окончания", "დასრულების თარიღი"),
        _title("End time", "Время окончания", "დასრულების დრო"),
        STATUS,
        _title("Place", "Место", "ადგილი"),
        _title("Service", "Услуга", "მომსახურება"),
        PARTY_SIZE,
        CUSTOMER,
        PHONE,
        CHANNEL,
        _title("Value", "Стоимость", "ღირებულება"),
        _title("Currency", "Валюта", "ვალუტა"),
        _title("Notes", "Заметки", "შენიშვნები"),
        TEST,
        CREATED,
    ),
    CsvExportKind.LEADS: (
        _title("Request ID", "ID заявки", "მოთხოვნის ID"),
        CREATED,
        STATUS,
        _title("Type", "Тип", "ტიპი"),
        CUSTOMER,
        PHONE,
        CHANNEL,
        _title("Requested date", "Желаемая дата", "სასურველი თარიღი"),
        PARTY_SIZE,
        _title("Budget", "Бюджет", "ბიუჯეტი"),
        _title("Details", "Подробности", "დეტალები"),
        TEST,
    ),
    CsvExportKind.CONTACTS: (
        _title("Customer ID", "ID клиента", "კლიენტის ID"),
        _title("Name", "Имя", "სახელი"),
        PHONE,
        _title("Phone confirmed", "Телефон подтверждён", "ტელეფონი დადასტურებულია"),
        _title("Language", "Язык", "ენა"),
        _title("Channels", "Каналы", "არხები"),
        _title("First contact", "Первый контакт", "პირველი კონტაქტი"),
        _title(
            "Sent STOP in",
            "Отписался (STOP) в",
            "გამოწერა გააუქმა (STOP)",
        ),
    ),
    CsvExportKind.CONVERSATIONS: (
        _title("Conversation ID", "ID разговора", "საუბრის ID"),
        CHANNEL,
        STATUS,
        CUSTOMER,
        PHONE,
        _title("Started", "Начат", "დაიწყო"),
        _title("Message time", "Время сообщения", "შეტყობინების დრო"),
        _title("Author", "Автор", "ავტორი"),
        _title("Message", "Сообщение", "შეტყობინება"),
    ),
    CsvExportKind.AUDIT_LOG: (
        _title("Time", "Время", "დრო"),
        _title("Operation", "Действие", "მოქმედება"),
        _title("Record type", "Тип записи", "ჩანაწერის ტიპი"),
        _title("Record ID", "ID записи", "ჩანაწერის ID"),
        _title("Person", "Кто", "ვინ"),
        _title("IP address", "IP-адрес", "IP მისამართი"),
    ),
}
