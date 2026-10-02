"""Conversations of the demo restaurant in Georgian: bookings."""

from app.registries.demo import demo_tool_calls as calls
from app.registries.demo.demo_activity_builder import DemoActivityBuilder
from app.registries.demo.demo_lines import assistant, customer, staff
from app.registries.demo.demo_words import day_word
from app.registries.demo.tbilisi_restaurant.restaurant_foundation import (
    COURTYARD_TABLE,
    HALL_TABLE,
    WINDOW_TABLE,
)
from app.schemas.constants.bookings import BookingStatus, LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationRating, ConversationStatus
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId

HELLO: str = "გამარჯობა! მე „მწვანე ეზოს“ AI ასისტენტი ვარ."
TELEGRAM = ChannelKind.TELEGRAM
WHATSAPP = ChannelKind.WHATSAPP
WEB = ChannelKind.WEB_CHAT


def record_georgian_booking_chats(
    story: DemoActivityBuilder, guests: dict[str, ContactDocument]
) -> None:
    """Georgian guests booking tables (and a wedding dinner)."""

    clock, talk, desk = story.clock, story.talk, story.desk
    # Nino books a table for tonight (or tomorrow's lunch) in Telegram.
    start = clock.ago(hours=4, minutes=10)
    slot = clock.next_slot()
    day, time = day_word(clock, slot, "ka", said_at=start), clock.clock_of(slot)
    booking_id = BookingId()
    confirmation = (
        f"დაჯავშნილია: {day}, {time}, 4 სტუმარი, ნინო. მაგიდას 15 წუთი "
        "გიტოვებთ, გაუქმება უფასოა ვიზიტამდე 3 საათით ადრე."
    )
    chat = talk.chat(
        guests["nino"],
        TELEGRAM,
        start,
        [
            customer(f"გამარჯობა! {day} {time}-ზე ოთხი კაცისთვის მაგიდა გექნებათ?"),
            assistant(
                f"{HELLO} {day} {time}-ზე დარბაზში ოთხკაციანი მაგიდა თავისუფალია. "
                "დავჯავშნო თქვენს სახელზე?",
                calls.availability(clock, desk.resource(HALL_TABLE), slot, 4),
            ),
            customer("დიახ, ნინოს სახელზე. ტელეფონი 599 11 22 33"),
            assistant(
                confirmation,
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(HALL_TABLE),
                    slot,
                    4,
                    "ნინო",
                    "+995599112233",
                    confirmation,
                ),
            ),
            customer("მადლობა! 🙏"),
            assistant("სიამოვნებით! გელოდებით „მწვანე ეზოში“."),
        ],
        rating=ConversationRating.GOOD,
        rated_by=story.owner_id,
    )
    desk.booking(
        guests["nino"],
        HALL_TABLE,
        slot,
        4,
        TELEGRAM,
        conversation=chat,
        booking_id=booking_id,
    )

    # Giorgi books the courtyard for tomorrow; the dinner took place.
    start = clock.past(-3, "12:15")
    visit = clock.at(-2, "19:00")
    booking_id = BookingId()
    confirmation = "დაჯავშნილია: ხვალ, 19:00, ეზო, 4 სტუმარი, გიორგი. გელოდებით!"
    chat = talk.chat(
        guests["giorgi"],
        WHATSAPP,
        start,
        [
            customer("სალამი, ხვალ 19:00-ზე 4 კაცზე ეზოში მაგიდა გაქვთ?"),
            assistant(
                f"{HELLO} ხვალ 19:00-ზე ეზოში ექვსადგილიანი მაგიდაა თავისუფალი — "
                "ოთხ სტუმარს მოუხერხებელი არ იქნება. ეზოში გამათბობლებიც გვაქვს. "
                "დავჯავშნო?",
                calls.availability(clock, desk.resource(COURTYARD_TABLE), visit, 4),
            ),
            customer("კი, გიორგის სახელზე"),
            assistant(
                confirmation,
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(COURTYARD_TABLE),
                    visit,
                    4,
                    "გიორგი",
                    "+995577223344",
                    confirmation,
                ),
            ),
        ],
        rating=ConversationRating.GOOD,
        rated_by=story.owner_id,
    )
    desk.booking(
        guests["giorgi"],
        COURTYARD_TABLE,
        visit,
        4,
        WHATSAPP,
        status=BookingStatus.COMPLETED,
        conversation=chat,
        booking_id=booking_id,
    )

    # Tamar asks about live music and books Friday by the window (open now).
    start = clock.ago(minutes=48)
    friday = clock.next_weekday(4, "20:00")
    booking_id = BookingId()
    confirmation = (
        "დაგიჯავშნეთ ფანჯარასთან მაგიდა პარასკევს 20:00-ზე, 2 სტუმარი, თამარი."
    )
    chat = talk.chat(
        guests["tamar"],
        WEB,
        start,
        [
            customer("გამარჯობა, პარასკევს ცოცხალი მუსიკა გაქვთ?"),
            assistant(
                f"{HELLO} დიახ, პარასკევობით და შაბათობით 20:00-დან გვაქვს გიტარა "
                "და ქართული მრავალხმიანობა 🎶 გნებავთ მაგიდის დაჯავშნა?",
                calls.search("ცოცხალი მუსიკა", [story.item("Когда у вас живая")], "ka"),
            ),
            customer(
                "კი, პარასკევს 20:00-ზე ორნი ვიქნებით, ფანჯარასთან თუ შეიძლება. თამარი"
            ),
            assistant(
                f"{confirmation} სცენა ფანჯრიდან კარგად ჩანს 🙂",
                calls.availability(clock, desk.resource(WINDOW_TABLE), friday, 2),
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(WINDOW_TABLE),
                    friday,
                    2,
                    "თამარი",
                    None,
                    confirmation,
                ),
            ),
            customer("ძალიან კარგი, მადლობა!"),
        ],
        status=ConversationStatus.OPEN,
    )
    desk.booking(
        guests["tamar"],
        WINDOW_TABLE,
        friday,
        2,
        WEB,
        conversation=chat,
        booking_id=booking_id,
    )

    # Levan asks for a wedding dinner: a banquet lead the manager won.
    start = clock.past(-22, "11:30")
    event = clock.at(-2, "18:00")
    lead_id = LeadId()
    details = (
        "ქორწილის შემდგომი ვახშამი, ~35 სტუმარი, ცალკე დარბაზი, "
        f"{clock.short_date(event)}"
    )
    chat = talk.chat(
        guests["levan"],
        TELEGRAM,
        start,
        [
            customer(
                "გამარჯობა! ქორწილის შემდეგ ვახშამს ვგეგმავთ, დაახლოებით 35 "
                "სტუმარი. ცალკე დარბაზი გაქვთ?"
            ),
            assistant(
                "გილოცავთ! 🎉 მე „მწვანე ეზოს“ AI ასისტენტი ვარ. ცალკე დარბაზი 45 "
                "სტუმრამდე ეტევა, საბანკეტო მენიუ 15 სტუმრიდან გვაქვს. ფასს და "
                "დეტალებს მენეჯერი შეგითანხმებთ — თარიღი და ტელეფონი მომწერეთ.",
                calls.search("ბანკეტი", [story.item("Банкетное меню")], "ka"),
            ),
            customer(
                f"{clock.short_date(event)}-ში, საღამოს 6-დან. ლევანი, 555 33 44 55"
            ),
            assistant(
                "მადლობა, ლევან! მოთხოვნა მენეჯერს გადავეცი — დღესვე დაგიკავშირდებათ.",
                calls.lead(
                    lead_id,
                    LeadType.BANQUET,
                    details,
                    "ლევანი",
                    "+995555334455",
                    str(clock.local_date_of(event)),
                    35,
                ),
            ),
            staff(
                "ლევან, გამარჯობა! თამარი ვარ, ადმინისტრატორი. დარბაზი თავისუფალია, "
                "მენიუს ვარიანტებს ახლავე გამოგიგზავნით 🙂",
                pause=2400,
            ),
        ],
    )
    desk.lead(
        guests["levan"],
        LeadType.BANQUET,
        details,
        TELEGRAM,
        chat.created_at,
        status=LeadStatus.WON,
        conversation=chat,
        requested_day=-2,
        party_size=35,
        budget="ერთ სტუმარზე 90-100 ლარი",
        lead_id=lead_id,
    )

    # Ana books for five the next evening.
    start = clock.past(-10, "10:05")
    visit = clock.at(-9, "19:00")
    booking_id = BookingId()
    confirmation = "დაჯავშნილია: ხვალ, 19:00, ეზო, 5 სტუმარი, ანა. გელოდებით!"
    chat = talk.chat(
        guests["ana"],
        WHATSAPP,
        start,
        [
            customer("ხვალ 19:00-ზე 5 კაცზე მაგიდა მინდა"),
            assistant(
                f"{HELLO} ხვალ 19:00-ზე ეზოში ექვსადგილიანი მაგიდაა თავისუფალი. "
                "დავჯავშნო ანას სახელზე?",
                calls.availability(clock, desk.resource(COURTYARD_TABLE), visit, 5),
            ),
            customer("კი"),
            assistant(
                confirmation,
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(COURTYARD_TABLE),
                    visit,
                    5,
                    "ანა",
                    "+995598445566",
                    confirmation,
                ),
            ),
        ],
    )
    desk.booking(
        guests["ana"],
        COURTYARD_TABLE,
        visit,
        5,
        WHATSAPP,
        status=BookingStatus.COMPLETED,
        conversation=chat,
        booking_id=booking_id,
    )
