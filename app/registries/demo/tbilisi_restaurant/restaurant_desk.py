"""
The demo restaurant's phone and front desk: a call the voice agent took,
bookings staff entered by hand, questions asked again and again, and the
owner's own test chat.
"""

from app.registries.demo import demo_tool_calls as calls
from app.registries.demo.demo_activity_builder import DemoActivityBuilder
from app.registries.demo.demo_lines import assistant, customer, voice_tool
from app.registries.demo.demo_words import day_word
from app.registries.demo.tbilisi_restaurant.restaurant_foundation import (
    COURTYARD_TABLE,
    HALL_TABLE,
    RESTAURANT_ASSISTANT_LINE,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import (
    CallGuardVerdict,
    CallOutcome,
    ConversationRating,
    ConversationStatus,
    MessageAuthor,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.bookings.prefixed_id import BookingId

PHONE = ChannelKind.PHONE
ASSISTANT = MessageAuthor.ASSISTANT
CALLER = MessageAuthor.CUSTOMER
# ElevenLabs conversation id of the demo call (the phone conversation's
# channel user id).
DEMO_CALL_ID: str = "conv_demo_7a1c3e5f9b2d4680"
OWNER_TEST_SESSION: str = "owner_test_3f9a1c7e5b2d4f60"


def record_front_desk(
    story: DemoActivityBuilder, guests: dict[str, ContactDocument]
) -> None:
    record_phone_booking(story, guests["davit"])
    clock, desk = story.clock, story.desk

    # Regulars who called the restaurant directly; staff entered the bookings.
    vakhtang = story.talk.contact(
        "ვახტანგ ქავთარაძე", "ka", phone="+995595112233", since=clock.ago(days=9)
    )
    desk.booking(
        vakhtang,
        COURTYARD_TABLE,
        clock.at(-7, "20:00"),
        6,
        PHONE,
        status=BookingStatus.COMPLETED,
        made_at=clock.past(-8, "12:40"),
        notes="Постоянный гость, любит стол у мангала",
    )
    guram = story.talk.contact(
        "Гурам Церетели", "ru", phone="+995577990011", since=clock.ago(days=1)
    )
    desk.booking(
        guram,
        HALL_TABLE,
        clock.upcoming(5, "19:00"),
        4,
        PHONE,
        made_at=clock.ago(hours=26),
        notes="Записала Тамар по телефону",
    )

    # Questions the knowledge base does not answer yet.
    desk.question(
        "Есть ли рядом зарядка для электромобиля?",
        "ru",
        clock.past(-5, "18:05"),
        occurrences=2,
    )
    desk.question(
        "Can I order a birthday cake from you?", "en", clock.past(-1, "12:30")
    )

    record_owner_test_chat(story)


def record_phone_booking(story: DemoActivityBuilder, caller: ContactDocument) -> None:
    """Davit calls; the voice agent books a table and answers about parking."""

    clock, desk = story.clock, story.desk
    start = clock.past(-2, "17:20")
    visit = clock.upcoming(3, "18:30")
    day = day_word(clock, visit, "ka", said_at=start)
    booking_id = BookingId()
    confirmation = f"დაჯავშნილია: {day}, 18:30, 4 სტუმარი, დავითი."
    chat = story.talk.chat(
        caller,
        PHONE,
        start,
        [
            voice_tool(
                calls.availability(clock, desk.resource(HALL_TABLE), visit, 4),
                pause=15,
            ),
            voice_tool(
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(HALL_TABLE),
                    visit,
                    4,
                    "დავითი",
                    "+995593456789",
                    confirmation,
                ),
                pause=28,
            ),
            voice_tool(
                calls.search("პარკინგი", [story.item("Есть ли парковка")], "ka"),
                pause=18,
            ),
        ],
        channel_user_id=DEMO_CALL_ID,
        rating=ConversationRating.GOOD,
        rated_by=story.owner_id,
    )
    desk.booking(
        caller, HALL_TABLE, visit, 4, PHONE, conversation=chat, booking_id=booking_id
    )
    story.talk.call(
        chat,
        caller="+995593456789",
        assistant_line=RESTAURANT_ASSISTANT_LINE,
        duration_seconds=82,
        transcript=[
            (
                0,
                ASSISTANT,
                "გამარჯობა, „მწვანე ეზო“, AI ასისტენტი გესაუბრებათ. "
                "ზარი შეიძლება ჩაიწეროს. რით დაგეხმაროთ?",
            ),
            (
                7,
                CALLER,
                f"გამარჯობა, {day} საღამოს ოთხ კაცზე მაგიდა მინდა, ექვსის ნახევარზე.",
            ),
            (
                15,
                ASSISTANT,
                f"ერთი წამით, ვამოწმებ... {day} 18:30-ზე დარბაზში "
                "ოთხკაციანი მაგიდა თავისუფალია. რა სახელზე დავჯავშნო?",
            ),
            (29, CALLER, "დავითი, დავით მაისურაძე."),
            (34, ASSISTANT, "ჯავშანში ჩავწერო ნომერი, საიდანაც რეკავთ?"),
            (39, CALLER, "კი, ეს ნომერი."),
            (
                43,
                ASSISTANT,
                f"{confirmation} დადასტურებას მესიჯით მიიღებთ. "
                "კიდევ რამეში ხომ არ დაგეხმაროთ?",
            ),
            (55, CALLER, "პარკინგი გაქვთ?"),
            (
                61,
                ASSISTANT,
                "საკუთარი პარკინგი არ გვაქვს, ახლოს ქალაქის ფასიანი "
                "პარკინგია — საათში 2 ლარი. ტაქსით მოსვლა უფრო მოსახერხებელია.",
            ),
            (74, CALLER, "გასაგებია, მადლობა."),
            (77, ASSISTANT, "არაფრის! გელოდებით „მწვანე ეზოში“. ნახვამდის!"),
        ],
        outcome=CallOutcome.BOOKING,
        cost_micro_usd=109_300,
        # Every value said is backed: the parking price is from the FAQ.
        guard_verdict=CallGuardVerdict.CLEAN,
    )


def record_owner_test_chat(story: DemoActivityBuilder) -> None:
    """The owner tried the assistant in the cabinet's test chat (sandbox)."""

    clock, desk = story.clock, story.desk
    start = clock.ago(minutes=95)
    visit = clock.upcoming(1, "19:00")
    tester = story.talk.contact(
        None,
        "ru",
        identities=[(ChannelKind.OWNER_TEST, OWNER_TEST_SESSION)],
        since=start,
    )
    story.talk.chat(
        tester,
        ChannelKind.OWNER_TEST,
        start,
        [
            customer("Сколько стоит хачапури по-аджарски?", pause=0),
            assistant(
                "Здравствуйте! Я AI-ассистент ресторана «Mtsvane Ezo». Хачапури "
                "по-аджарски — 22 лари, готовим около 20 минут.",
                calls.price("хачапури по-аджарски", story.item("Хачапури по-аджарски")),
            ),
            customer("А завтра в 19:00 на двоих свободно?"),
            assistant(
                "Да, завтра в 19:00 в зале есть свободный стол. На чьё имя "
                "забронировать?",
                calls.availability(clock, desk.resource(HALL_TABLE), visit, 2),
            ),
        ],
        status=ConversationStatus.OPEN,
        is_sandbox=True,
    )
