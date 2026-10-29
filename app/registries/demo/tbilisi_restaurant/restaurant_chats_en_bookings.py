"""Conversations of the demo restaurant in English: bookings."""

from app.registries.demo import demo_tool_calls as calls
from app.registries.demo.demo_activity_builder import DemoActivityBuilder
from app.registries.demo.demo_lines import assistant, customer, staff
from app.registries.demo.demo_words import day_word
from app.registries.demo.tbilisi_restaurant.restaurant_foundation import (
    COURTYARD_TABLE,
    HALL_TABLE,
    WINDOW_TABLE,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationRating, ConversationStatus
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.handoffs.prefixed_id import HandoffId

HELLO: str = "Hello! I'm the AI assistant of Mtsvane Ezo."
TELEGRAM = ChannelKind.TELEGRAM
WHATSAPP = ChannelKind.WHATSAPP
WEB = ChannelKind.WEB_CHAT


def record_english_booking_chats(
    story: DemoActivityBuilder, guests: dict[str, ContactDocument]
) -> None:
    clock, talk, desk = story.clock, story.talk, story.desk

    # Sarah books by the window and has a walnut allergy: the chef confirms.
    start = clock.ago(hours=2, minutes=15)
    slot = clock.next_slot(("19:30", "20:00", "13:30", "14:00"))
    day, time = day_word(clock, slot, "en", said_at=start), clock.clock_of(slot)
    booking_id, handoff_id = BookingId(), HandoffId()
    confirmation = f"Booked: {day}, {time}, window table for 2, under Sarah."
    summary = (
        "Сильная аллергия на грецкие орехи; гость забронировал столик у окна, "
        "нужно подтверждение шефа"
    )
    chat = talk.chat(
        guests["sarah"],
        WHATSAPP,
        start,
        [
            customer(
                f"Hi! Could we get a table for two {day} at {time}? "
                "Ideally by the window"
            ),
            assistant(
                f"{HELLO} Yes, a window table for two is free {day} at {time}. "
                "Shall I book it under your name?",
                calls.availability(clock, desk.resource(WINDOW_TABLE), slot, 2),
            ),
            customer(
                "Yes please, Sarah. One more thing: I have a severe walnut allergy. "
                "Is that OK?"
            ),
            assistant(
                f"{confirmation} Many of our dishes contain walnuts, so I've passed "
                "your allergy to the hall manager — the chef will confirm what is "
                "safe for you.",
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(WINDOW_TABLE),
                    slot,
                    2,
                    "Sarah",
                    "+447700900123",
                    confirmation,
                ),
                calls.handoff(
                    handoff_id,
                    HandoffReason.PROFILE_RULE,
                    summary,
                    HandoffUrgency.NORMAL,
                ),
            ),
            staff(
                "Hi Sarah, this is Tamar, the hall manager. Our chef will cook your "
                "dishes without walnuts and in separate pans, and we'll mark your "
                "table. See you soon!",
                pause=1500,
            ),
            customer("Thank you so much, that's really reassuring!", pause=240),
        ],
        status=ConversationStatus.OPEN,
        rating=ConversationRating.GOOD,
        rated_by=story.owner_id,
    )
    desk.booking(
        guests["sarah"],
        WINDOW_TABLE,
        slot,
        2,
        WHATSAPP,
        conversation=chat,
        notes="Severe walnut allergy — chef informed",
        booking_id=booking_id,
    )
    desk.handoff(
        chat,
        HandoffReason.PROFILE_RULE,
        summary,
        HandoffUrgency.NORMAL,
        resolved_after_minutes=26,
        handoff_id=handoff_id,
    )

    # James books dinner for two later this week.
    start = clock.past(-1, "15:30")
    visit = clock.upcoming(3, "19:00")
    day = day_word(clock, visit, "en", said_at=start)
    booking_id = BookingId()
    confirmation = f"You're booked {day} at 19:00, table for 2, under James."
    chat = talk.chat(
        guests["james"],
        WEB,
        start,
        [
            customer(f"Hi, can I book a table for two {day} at 7pm?"),
            assistant(
                f"{HELLO} Yes, {day} at 19:00 a table in the hall is free. "
                "May I have your name and phone number?",
                calls.availability(clock, desk.resource(HALL_TABLE), visit, 2),
            ),
            customer("James O'Connor, +353 86 123 4567"),
            assistant(
                f"{confirmation} We hold tables for 15 minutes.",
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(HALL_TABLE),
                    visit,
                    2,
                    "James",
                    "+353861234567",
                    confirmation,
                ),
            ),
        ],
    )
    desk.booking(
        guests["james"],
        HALL_TABLE,
        visit,
        2,
        WEB,
        conversation=chat,
        booking_id=booking_id,
    )

    # Lukas books lunch, then cancels two hours later.
    start = clock.past(-3, "10:00")
    visit = clock.upcoming(2, "14:00")
    day = day_word(clock, visit, "en", said_at=start)
    booking_id = BookingId()
    confirmation = f"Done: {day}, 14:00, table for 2, under Lukas."
    cancelled = "Your booking is cancelled. Hope to see you another time!"
    chat = talk.chat(
        guests["lukas"],
        WEB,
        start,
        [
            customer(f"Hello, a table for 2 {day} at 14:00, please. Name: Lukas"),
            assistant(
                f"{HELLO} {confirmation}",
                calls.availability(clock, desk.resource(WINDOW_TABLE), visit, 2),
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(WINDOW_TABLE),
                    visit,
                    2,
                    "Lukas",
                    None,
                    confirmation,
                ),
            ),
            customer("Sorry, our flight changed — please cancel it", pause=7200),
            assistant(
                cancelled,
                calls.cancellation(
                    clock, booking_id, desk.resource(WINDOW_TABLE), visit, 2, cancelled
                ),
            ),
        ],
    )
    desk.booking(
        guests["lukas"],
        WINDOW_TABLE,
        visit,
        2,
        WEB,
        status=BookingStatus.CANCELLED,
        conversation=chat,
        booking_id=booking_id,
        made_at=clock.later(start, 1),
    )

    # Emily asks for vegetarian food and books lunch; they came.
    start = clock.past(-5, "11:00")
    visit = clock.at(-4, "13:30")
    booking_id = BookingId()
    confirmation = "Booked: tomorrow, 13:30, table for 2, under Emily."
    chat = talk.chat(
        guests["emily"],
        TELEGRAM,
        start,
        [
            customer("Hi! Do you have vegetarian dishes? Thinking of lunch tomorrow"),
            assistant(
                f"{HELLO} Yes: pkhali, badrijani with walnut paste, mushroom khinkali "
                "and lobio in a clay pot. Shall I book a table?",
                calls.search(
                    "vegetarian dishes",
                    [story.item("Пхали"), story.item("Хинкали с грибами")],
                    "en",
                ),
            ),
            customer("Yes, 13:30 for two, Emily"),
            assistant(
                confirmation,
                calls.availability(clock, desk.resource(WINDOW_TABLE), visit, 2),
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(WINDOW_TABLE),
                    visit,
                    2,
                    "Emily",
                    None,
                    confirmation,
                ),
            ),
        ],
    )
    desk.booking(
        guests["emily"],
        WINDOW_TABLE,
        visit,
        2,
        TELEGRAM,
        status=BookingStatus.COMPLETED,
        conversation=chat,
        booking_id=booking_id,
    )

    # Priya brings three children (open conversation).
    start = clock.ago(minutes=27)
    visit = clock.upcoming(2, "20:00")
    day = day_word(clock, visit, "en", said_at=start)
    booking_id = BookingId()
    confirmation = f"Booked: {day}, 20:00, courtyard table for 5, under Priya."
    chat = talk.chat(
        guests["priya"],
        WEB,
        start,
        [
            customer(f"Hi! 2 adults + 3 kids {day} at 8pm — do you have high chairs?"),
            assistant(
                f"{HELLO} Yes, we have high chairs, a kids' menu and a closed "
                "courtyard. A courtyard table for five is free then. Shall I book it?",
                calls.search(
                    "high chairs kids", [story.item("Можно ли прийти с детьми")]
                ),
                calls.availability(clock, desk.resource(COURTYARD_TABLE), visit, 5),
            ),
            customer("Yes! Priya, +91 98123 45678"),
            assistant(
                f"{confirmation} We'll put two high chairs at the table.",
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(COURTYARD_TABLE),
                    visit,
                    5,
                    "Priya",
                    "+919812345678",
                    confirmation,
                ),
            ),
        ],
        status=ConversationStatus.OPEN,
    )
    desk.booking(
        guests["priya"],
        COURTYARD_TABLE,
        visit,
        5,
        WEB,
        conversation=chat,
        notes="2 high chairs",
        booking_id=booking_id,
    )
