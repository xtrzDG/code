"""Conversations of the demo restaurant in Georgian: questions."""

from app.registries.demo import demo_tool_calls as calls
from app.registries.demo.demo_activity_builder import DemoActivityBuilder
from app.registries.demo.demo_lines import assistant, customer, staff
from app.registries.demo.tbilisi_restaurant.restaurant_foundation import (
    HALL_TABLE,
    SITE,
    WINDOW_TABLE,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId

HELLO: str = "გამარჯობა! მე „მწვანე ეზოს“ AI ასისტენტი ვარ."
TELEGRAM = ChannelKind.TELEGRAM
WHATSAPP = ChannelKind.WHATSAPP
WEB = ChannelKind.WEB_CHAT


def record_georgian_question_chats(
    story: DemoActivityBuilder, guests: dict[str, ContactDocument]
) -> None:
    """Georgian guests asking prices, hours and favours."""

    clock, talk, desk = story.clock, story.talk, story.desk
    # Mariam compares prices, then books lunch for three.
    start = clock.past(-19, "16:40")
    visit = clock.at(-18, "13:00")
    booking_id = BookingId()
    confirmation = "დაგიჯავშნეთ: ხვალ, 13:00, 3 სტუმარი, მარიამი. კარგ მადას გისურვებთ!"
    chat = talk.chat(
        guests["mariam"],
        WEB,
        start,
        [
            customer("რა ღირს აჭარული ხაჭაპური და ხინკალი?"),
            assistant(
                f"{HELLO} აჭარული ხაჭაპური — 22 ლარი. ხინკალი ხორცით — 1.80 ლარი "
                "ცალი, სოკოთი და სულგუნით — 1.70 ლარი (მინიმუმ 5 ცალი).",
                calls.price("აჭარული ხაჭაპური", story.item("Хачапури по-аджарски")),
                calls.price(
                    "ხინკალი",
                    story.item("Хинкали с говядиной"),
                    story.item("Хинкали с грибами"),
                ),
            ),
            customer("ხვალ 13:00-ზე სამნი მოვალთ, მარიამის სახელზე"),
            assistant(
                confirmation,
                calls.availability(clock, desk.resource(HALL_TABLE), visit, 3),
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(HALL_TABLE),
                    visit,
                    3,
                    "მარიამი",
                    None,
                    confirmation,
                ),
            ),
        ],
    )
    desk.booking(
        guests["mariam"],
        HALL_TABLE,
        visit,
        3,
        WEB,
        status=BookingStatus.COMPLETED,
        conversation=chat,
        booking_id=booking_id,
    )

    # Irakli books at night (after hours) and does not come.
    start = clock.past(-13, "00:40")
    visit = clock.at(-13, "20:00")
    booking_id = BookingId()
    confirmation = "დაჯავშნილია: დღეს, 20:00, 2 სტუმარი, ირაკლი. გელოდებით!"
    chat = talk.chat(
        guests["irakli"],
        TELEGRAM,
        start,
        [
            customer("დღეს საღამოს 8-ზე ორნი შეგვიძლია მოსვლა?"),
            assistant(
                f"{HELLO} ღამითაც გპასუხობთ 🙂 დღეს 20:00-ზე ფანჯარასთან "
                "ორკაციანი მაგიდა თავისუფალია. რა სახელზე დავჯავშნო?",
                calls.availability(clock, desk.resource(WINDOW_TABLE), visit, 2),
            ),
            customer("ირაკლი"),
            assistant(
                confirmation,
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(WINDOW_TABLE),
                    visit,
                    2,
                    "ირაკლი",
                    None,
                    confirmation,
                ),
            ),
        ],
    )
    desk.booking(
        guests["irakli"],
        WINDOW_TABLE,
        visit,
        2,
        TELEGRAM,
        status=BookingStatus.NO_SHOW,
        conversation=chat,
        booking_id=booking_id,
    )

    # Lasha asks for gluten-free khachapuri: not in the knowledge yet.
    start = clock.past(-6, "15:00")
    question_id = UnansweredQuestionId()
    question = "გაქვთ თუ არა უგლუტენო ხაჭაპური?"
    talk.chat(
        guests["lasha"],
        WEB,
        start,
        [
            customer("უგლუტენო ხაჭაპური გაქვთ?"),
            assistant(
                f"{HELLO} ამის შესახებ ზუსტი ინფორმაცია არ მაქვს — კითხვა გუნდს "
                "გადავეცი. შეგიძლიათ დარეკოთ: +995 32 219 00 19.",
                calls.search("უგლუტენო ხაჭაპური", [], "ka"),
                calls.unanswered(question_id, question),
            ),
            customer("კარგი, მადლობა"),
        ],
    )
    desk.question(
        question, "ka", clock.later(start, 2), occurrences=2, question_id=question_id
    )

    # Giorgi forgot his scarf: handed to the hall manager, resolved.
    start = clock.past(-7, "13:00")
    handoff_id = HandoffId()
    summary = "Гость вчера забыл у нас синий шарф и ищет его"
    chat = talk.chat(
        guests["giorgi"],
        WHATSAPP,
        start,
        [
            customer("გუშინ თქვენთან ვიყავი და ლურჯი შარფი დამრჩა. ხომ არ გინახავთ?"),
            assistant(
                "ვწუხვარ! მე AI ასისტენტი ვარ — ადმინისტრატორს გადავეცი, "
                "შეამოწმებს და აქვე მოგწერთ.",
                calls.handoff(
                    handoff_id,
                    HandoffReason.CUSTOMER_REQUEST,
                    summary,
                    HandoffUrgency.LOW,
                ),
            ),
            staff("გიორგი, გამარჯობა! შარფი ვიპოვეთ, ადმინისტრატორთან გელოდებათ 🙂"),
            customer("დიდი მადლობა!", pause=600),
        ],
    )
    desk.handoff(
        chat,
        HandoffReason.CUSTOMER_REQUEST,
        summary,
        HandoffUrgency.LOW,
        resolved_after_minutes=6,
        handoff_id=handoff_id,
    )

    # Eka asks early in the morning about the hours and delivery.
    start = clock.past(-4, "09:10")
    talk.chat(
        guests["eka"],
        TELEGRAM,
        start,
        [
            customer("დილა მშვიდობისა! დღეს რომელ საათზე იხსნებით? მიტანა გაქვთ?"),
            assistant(
                "დილა მშვიდობისა! მე „მწვანე ეზოს“ AI ასისტენტი ვარ. დღეს 12:00-დან "
                "ვართ ღია. მიტანა Wolt-ით და Glovo-თი შეგიძლიათ: "
                f"{SITE}/delivery",
                calls.search("მიტანა", [story.item("Есть ли доставка")], "ka"),
                calls.link(BusinessLinkKind.DELIVERY, f"{SITE}/delivery"),
            ),
            customer("სუპერ, მადლობა"),
        ],
    )

    # An impatient guest asks about Sunday hours.
    talk.chat(
        guests["zurab"],
        TELEGRAM,
        clock.past(-26, "19:00"),
        [
            customer("ალო?? 10 წუთია ვწერ და პასუხი არ არის"),
            assistant(
                "ბოდიში მოლოდინისთვის! მე „მწვანე ეზოს“ AI ასისტენტი ვარ. "
                "რით დაგეხმაროთ?"
            ),
            customer("კვირას რომლამდე მუშაობთ?"),
            assistant(
                "კვირას 12:00-დან 22:00-მდე ვართ ღია. მაგიდა ხომ არ დაგიჯავშნოთ?"
            ),
            customer("არა, ჯერ არა"),
        ],
    )
