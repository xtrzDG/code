"""
The headings of a segment's CSV in the owner's language, in the order of
its cells (`segment_rows` writes exactly these). The columns a campaign
needs: who, how to reach them, where they asked not to be messaged.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text


def _title(en: str, ru: str, ka: str) -> LocalizedText:
    return build_localized_text(en=en, ru=ru, ka=ka)


SEGMENT_CSV_COLUMNS: tuple[LocalizedText, ...] = (
    _title("Customer ID", "ID клиента", "კლიენტის ID"),
    _title("Name", "Имя", "სახელი"),
    _title("Phone", "Телефон", "ტელეფონი"),
    _title("Phone confirmed", "Телефон подтверждён", "ტელეფონი დადასტურებულია"),
    _title("Language", "Язык", "ენა"),
    _title("Channels", "Каналы", "არხები"),
    _title("Tags", "Метки", "იარლიყები"),
    _title("VIP", "VIP", "VIP"),
    _title("Bookings", "Брони", "ჯავშნები"),
    _title("Last activity", "Последняя активность", "ბოლო აქტივობა"),
    _title(
        "Sent STOP in",
        "Отписался (STOP) в",
        "გამოწერა გააუქმა (STOP)",
    ),
)
