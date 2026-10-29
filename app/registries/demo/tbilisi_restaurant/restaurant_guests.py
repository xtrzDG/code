"""Guests of the Tbilisi demo restaurant and where they write from."""

from app.registries.demo.demo_activity_builder import DemoActivityBuilder
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ContactDocument

TELEGRAM = ChannelKind.TELEGRAM
WHATSAPP = ChannelKind.WHATSAPP
WEB = ChannelKind.WEB_CHAT

# key: (name, language, channel, channel user id, phone, days known)
GUESTS: dict[str, tuple[str | None, str, ChannelKind, str, str | None, int]] = {
    "nino": ("ნინო ბერიძე", "ka", TELEGRAM, "5012345601", "+995599112233", 40),
    "giorgi": ("გიორგი კაპანაძე", "ka", WHATSAPP, "995577223344", "+995577223344", 30),
    "tamar": ("თამარ ლომიძე", "ka", WEB, "visitor_4f1c2a9b7e3d5a10", None, 1),
    "levan": ("ლევან ჩხეიძე", "ka", TELEGRAM, "5012345602", "+995555334455", 29),
    "ana": ("ანა ჯაფარიძე", "ka", WHATSAPP, "995598445566", "+995598445566", 12),
    "mariam": ("მარიამ გელაშვილი", "ka", WEB, "visitor_9a7b3c1d2e4f6a80", None, 20),
    "irakli": ("ირაკლი ბაქრაძე", "ka", TELEGRAM, "5012345603", None, 15),
    "lasha": ("ლაშა წიკლაური", "ka", WEB, "visitor_1b2c3d4e5f6a7b8c", None, 7),
    "eka": ("ეკა აბაშიძე", "ka", TELEGRAM, "5012345604", None, 5),
    "zurab": (None, "ka", TELEGRAM, "5012345605", None, 27),
    "anna": ("Анна Смирнова", "ru", TELEGRAM, "5012345606", "+79161234567", 26),
    "dmitry": ("Дмитрий Ковалёв", "ru", WHATSAPP, "79035556677", "+79035556677", 1),
    "elena": (
        "Елена Петрова",
        "ru",
        WEB,
        "visitor_c0ffee11d00d4a5b",
        "+995591778899",
        2,
    ),
    "sergey": ("Сергей Иванов", "ru", TELEGRAM, "5012345607", "+995555667788", 16),
    "olga": ("Ольга Морозова", "ru", WHATSAPP, "375291112233", "+375291112233", 5),
    "maxim": (
        "Максим Волков",
        "ru",
        WEB,
        "visitor_aa11bb22cc33dd44",
        "+995592001122",
        2,
    ),
    "victoria": ("Виктория Кузнецова", "ru", WEB, "visitor_5e6f7a8b9c0d1e2f", None, 1),
    "irina": ("Ирина Соколова", "ru", TELEGRAM, "5012345608", None, 2),
    "artem": ("Артём Новиков", "ru", WHATSAPP, "77017654321", "+77017654321", 8),
    "pavel": ("Павел", "ru", WEB, "visitor_77ab12cd34ef56a0", None, 18),
    "natalia": ("Наталья", "ru", TELEGRAM, "5012345609", None, 13),
    "igor": ("Игорь Лебедев", "ru", WHATSAPP, "79267778899", "+79267778899", 29),
    "alexey": ("Алексей", "ru", WEB, "visitor_0d1e2f3a4b5c6d7e", None, 21),
    "sarah": ("Sarah Mitchell", "en", WHATSAPP, "447700900123", "+447700900123", 1),
    "james": (
        "James O'Connor",
        "en",
        WEB,
        "visitor_3c4d5e6f7a8b9c0d",
        "+353861234567",
        2,
    ),
    "lukas": ("Lukas Weber", "en", WEB, "visitor_8b9c0d1e2f3a4b5c", None, 3),
    "emily": ("Emily Chen", "en", TELEGRAM, "5012345610", None, 6),
    "tom": ("Tom Harris", "en", WHATSAPP, "447911123456", "+447911123456", 4),
    "priya": (
        "Priya Sharma",
        "en",
        WEB,
        "visitor_6f7a8b9c0d1e2f3a",
        "+919812345678",
        1,
    ),
    "michael": ("Michael Brown", "en", WEB, "visitor_2a3b4c5d6e7f8a9b", None, 17),
    "hannah": ("Hannah", "en", TELEGRAM, "5012345611", None, 28),
    "daniel": ("Daniel Fischer", "en", WHATSAPP, "4915112345678", "+4915112345678", 14),
    "olivia": ("Olivia Martin", "en", WEB, "visitor_9c0d1e2f3a4b5c6d", None, 9),
    "noa": ("נועה כהן", "he", WHATSAPP, "972501234567", "+972501234567", 10),
    "itay": ("איתי לוי", "he", WEB, "visitor_4b5c6d7e8f9a0b1c", None, 7),
    "ahmad": ("أحمد الخطيب", "ar", WHATSAPP, "971501234567", "+971501234567", 13),
    "layla": ("ليلى حداد", "ar", WEB, "visitor_e1f2a3b4c5d6e7f8", None, 4),
    "davit": ("დავით მაისურაძე", "ka", ChannelKind.PHONE, "", "+995593456789", 2),
}


def register_guests(story: DemoActivityBuilder) -> dict[str, ContactDocument]:
    """Every guest as a contact, known since the first time they wrote."""

    guests: dict[str, ContactDocument] = {}
    for key, (name, language, channel, user_id, phone, days) in GUESTS.items():
        guests[key] = story.talk.contact(
            name,
            language,
            identities=[] if channel is ChannelKind.PHONE else [(channel, user_id)],
            phone=phone,
            # WhatsApp senders and callers prove their number.
            is_phone_verified=channel in (WHATSAPP, ChannelKind.PHONE),
            since=story.clock.ago(days=days, hours=3),
        )

    return guests
