"""Bookings the Berlin demo salon's guests made in chats (German and English)."""

from app.registries.demo import demo_tool_calls as calls
from app.registries.demo.berlin_salon.salon_foundation import LENA, MEHMET, SOFIA
from app.registries.demo.demo_activity_builder import DemoActivityBuilder
from app.registries.demo.demo_lines import assistant, customer
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationRating, ConversationStatus
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.bookings.prefixed_id import BookingId

HALLO: str = "Ich bin der KI-Assistent vom Studio Lindenblatt."
HELLO: str = "I'm the AI assistant of Studio Lindenblatt."
WHATSAPP = ChannelKind.WHATSAPP
INSTAGRAM = ChannelKind.INSTAGRAM
WEB = ChannelKind.WEB_CHAT
PHONE = ChannelKind.PHONE


def record_salon_booking_chats(story: DemoActivityBuilder) -> None:
    clock, talk, desk = story.clock, story.talk, story.desk
    # Julia's balayage with Lena last Friday.
    julia = salon_guest(
        story, "Julia Becker", "de", WHATSAPP, "4915223344556", "+4915223344556"
    )
    visit = clock.last_weekday(4, "11:00")
    start = clock.later(visit, -4000)
    booking_id = BookingId()
    confirmation = "Gebucht: Freitag, 11:00–14:00, Balayage bei Lena."
    chat = talk.chat(
        julia,
        WHATSAPP,
        start,
        [
            customer("Hallo! Hätte Lena am Freitag um 11 Zeit für Balayage?"),
            assistant(
                f"Hi Julia! {HALLO} Freitag 11:00 bei Lena ist frei — Balayage dauert "
                "etwa 3 Stunden und kostet 160 € (mittellanges Haar). Soll ich buchen?",
                calls.availability(clock, desk.resource(LENA), visit, 1, minutes=180),
                calls.price("Balayage", story.item("Balayage")),
            ),
            customer("Ja bitte!"),
            assistant(
                f"{confirmation} Bis dann! ✨",
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(LENA),
                    visit,
                    1,
                    "Julia",
                    "+4915223344556",
                    confirmation,
                    minutes=180,
                ),
            ),
        ],
        rating=ConversationRating.GOOD,
        rated_by=story.owner_id,
    )
    desk.booking(
        julia,
        LENA,
        visit,
        1,
        WHATSAPP,
        BookingStatus.COMPLETED,
        180,
        chat,
        booking_id=booking_id,
    )

    # Tom books a men's haircut with Mehmet for Wednesday.
    tom = salon_guest(
        story, "Tom Richter", "de", WEB, "visitor_de11aa22bb33cc44", days=1
    )
    start = clock.ago(hours=6)
    visit = clock.next_weekday(2, "17:30")
    booking_id = BookingId()
    confirmation = "Erledigt: Mittwoch, 17:30, Herrenhaarschnitt bei Mehmet, für Tom."
    chat = talk.chat(
        tom,
        WEB,
        start,
        [
            customer("Moin, geht Mittwoch um 17:30 ein Herrenschnitt bei Mehmet?"),
            assistant(
                f"Moin! {HALLO} Mittwoch 17:30 bei Mehmet ist frei, "
                "Herrenschnitt 35 €. "
                "Auf welchen Namen?",
                calls.availability(clock, desk.resource(MEHMET), visit, 1, minutes=30),
            ),
            customer("Tom Richter"),
            assistant(
                f"{confirmation} Bis Mittwoch!",
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(MEHMET),
                    visit,
                    1,
                    "Tom",
                    None,
                    confirmation,
                    minutes=30,
                ),
            ),
        ],
    )
    desk.booking(
        tom, MEHMET, visit, 1, WEB, minutes=30, conversation=chat, booking_id=booking_id
    )

    # Emma asks on Instagram about a lash lift and books Saturday.
    emma = salon_guest(story, "Emma Wilson", "en", INSTAGRAM, "17841455500011")
    visit = clock.last_weekday(5, "10:30")
    start = clock.later(visit, -2300)
    booking_id = BookingId()
    confirmation = "Booked: Saturday, 10:30, lash lift with Sofia."
    chat = talk.chat(
        emma,
        INSTAGRAM,
        start,
        [
            customer("Hey! How much is a lash lift? And is Saturday morning possible?"),
            assistant(
                f"Hi Emma! {HELLO} A lash lift is €55 and takes about an hour. "
                "Saturday "
                "at 10:30 with Sofia is free — shall I book it?",
                calls.price("lash lift", story.item("Wimpernlifting")),
                calls.availability(clock, desk.resource(SOFIA), visit, 1, minutes=60),
            ),
            customer("Yes please 🙏"),
            assistant(
                f"{confirmation} See you!",
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(SOFIA),
                    visit,
                    1,
                    "Emma",
                    None,
                    confirmation,
                    minutes=60,
                ),
            ),
        ],
    )
    desk.booking(
        emma,
        SOFIA,
        visit,
        1,
        INSTAGRAM,
        BookingStatus.COMPLETED,
        60,
        chat,
        booking_id=booking_id,
    )

    # Aylin is ill and cancels her colour appointment.
    aylin = salon_guest(
        story, "Aylin Yılmaz", "de", WHATSAPP, "4917634455667", "+4917634455667"
    )
    visit = clock.next_weekday(3, "15:00")
    booking_id = BookingId()
    cancelled = "Dein Termin am Donnerstag um 15:00 ist storniert."
    talk.chat(
        aylin,
        WHATSAPP,
        clock.ago(hours=26),
        [
            customer(
                "Hallo, ich muss meinen Termin Donnerstag 15 Uhr absagen, bin krank 🤒"
            ),
            assistant(
                f"Gute Besserung, Aylin! {HALLO} {cancelled} Schreib einfach, wenn du "
                "einen neuen Termin möchtest.",
                calls.cancellation(
                    clock, booking_id, desk.resource(LENA), visit, 1, cancelled
                ),
            ),
        ],
    )
    desk.booking(
        aylin,
        LENA,
        visit,
        1,
        WHATSAPP,
        BookingStatus.CANCELLED,
        90,
        made_at=clock.ago(days=8),
        booking_id=booking_id,
    )

    # Sophie books a manicure (open conversation).
    sophie = salon_guest(
        story, "Sophie Martin", "en", WEB, "visitor_de99aa88bb77cc66", days=0
    )
    visit = clock.next_weekday(4, "12:00")
    booking_id = BookingId()
    confirmation = "Booked: Friday, 12:00, Shellac manicure with Sofia, for Sophie."
    chat = talk.chat(
        sophie,
        WEB,
        clock.ago(minutes=80),
        [
            customer(
                "Hi! Is Sofia free on Friday at noon for a shellac manicure? Sophie"
            ),
            assistant(
                f"Hi Sophie! {HELLO} {confirmation} It takes about an hour and "
                "costs €42.",
                calls.availability(clock, desk.resource(SOFIA), visit, 1, minutes=60),
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(SOFIA),
                    visit,
                    1,
                    "Sophie",
                    None,
                    confirmation,
                    minutes=60,
                ),
            ),
            customer("Perfect, thanks!"),
        ],
        status=ConversationStatus.OPEN,
    )
    desk.booking(
        sophie,
        SOFIA,
        visit,
        1,
        WEB,
        minutes=60,
        conversation=chat,
        booking_id=booking_id,
    )


def salon_guest(
    story: DemoActivityBuilder,
    name: str,
    language: str,
    channel: ChannelKind,
    user_id: str,
    phone: str | None = None,
    days: int = 20,
) -> ContactDocument:
    """A guest known in one channel since `days` ago."""

    return story.talk.contact(
        name,
        language,
        [(channel, user_id)],
        phone=phone,
        is_phone_verified=channel is WHATSAPP,
        since=story.clock.ago(days=days),
    )
