"""A few weeks of the Berlin demo salon: chats in German and English, bookings."""

from app.contracts.registries import PlanRegistryContract
from app.registries.demo import demo_tool_calls as calls
from app.registries.demo.berlin_salon.salon_autotests import (
    build_salon_autotest_results,
)
from app.registries.demo.berlin_salon.salon_chats import (
    record_salon_booking_chats,
    salon_guest,
)
from app.registries.demo.berlin_salon.salon_services import LENA, MEHMET
from app.registries.demo.demo_activity_builder import DemoActivityBuilder
from app.registries.demo.demo_autotests import finished_run
from app.registries.demo.demo_billing import billing_details, paid_subscription
from app.registries.demo.demo_lines import assistant, customer
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.dto.demo_data import DemoActivityRequest, DemoBusinessActivity
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId

HALLO: str = "Ich bin der KI-Assistent vom Studio Lindenblatt."
HELLO: str = "I'm the AI assistant of Studio Lindenblatt."
WHATSAPP = ChannelKind.WHATSAPP
INSTAGRAM = ChannelKind.INSTAGRAM
WEB = ChannelKind.WEB_CHAT
PHONE = ChannelKind.PHONE


def build_salon_activity(
    request: DemoActivityRequest, plan_registry: PlanRegistryContract
) -> DemoBusinessActivity:
    story = DemoActivityBuilder(request)
    clock, talk, desk = story.clock, story.talk, story.desk
    record_salon_booking_chats(story)

    # Lukas asks about children's haircuts: not answered by the profile.
    lukas = salon_guest(
        story, "Lukas Hoffmann", "de", WEB, "visitor_de55ee66ff770011", days=9
    )
    question_id = UnansweredQuestionId()
    question = "Schneidet ihr auch Kinderhaare?"
    start = clock.past(-9, "13:00")
    talk.chat(
        lukas,
        WEB,
        start,
        [
            customer("Schneidet ihr auch Kinderhaare? Mein Sohn ist 6"),
            assistant(
                f"Hallo! {HALLO} Dazu habe ich leider keine Infos — ich gebe die Frage "
                "an das Team weiter.",
                calls.search("Kinderhaarschnitt", [], "de"),
                calls.unanswered(question_id, question),
            ),
        ],
    )
    desk.question(
        question, "de", clock.later(start, 1), occurrences=2, question_id=question_id
    )

    # Marco is unhappy with his colour: an urgent handoff to Lena.
    marco = salon_guest(
        story, "Marco Rossi", "en", WHATSAPP, "393471234567", "+393471234567"
    )
    handoff_id = HandoffId()
    summary = (
        "Farbe nach dem Tönen zu orange; möchte sie diese Woche korrigieren lassen"
    )
    chat = talk.chat(
        marco,
        WHATSAPP,
        clock.past(-5, "18:00"),
        [
            customer(
                "Hi, I had my colour done yesterday and it turned out way too orange."
            ),
            assistant(
                f"I'm really sorry, Marco. {HELLO} I've passed this to Lena "
                "right away — "
                "she'll message you here to find a time to fix it.",
                calls.handoff(
                    handoff_id, HandoffReason.COMPLAINT, summary, HandoffUrgency.HIGH
                ),
            ),
        ],
    )
    desk.handoff(
        chat,
        HandoffReason.COMPLAINT,
        summary,
        HandoffUrgency.HIGH,
        handoff_id=handoff_id,
    )

    # Regulars who phoned; the owner entered the bookings.
    for name, resource, visit, service, status in (
        (
            "Hanna Schulz",
            LENA,
            clock.last_weekday(2, "10:00"),
            story.item("Ansatzfarbe"),
            BookingStatus.COMPLETED,
        ),
        (
            "Felix Wagner",
            MEHMET,
            clock.last_weekday(3, "18:00"),
            story.item("Herrenhaarschnitt"),
            BookingStatus.NO_SHOW,
        ),
        (
            "Clara Neumann",
            LENA,
            clock.next_weekday(5, "11:00"),
            story.item("Damenhaarschnitt"),
            BookingStatus.CONFIRMED,
        ),
    ):
        regular = talk.contact(name, "de", since=clock.ago(days=25))
        minutes = int(service.duration_minutes or 60)
        desk.booking(
            regular, resource, visit, 1, PHONE, status, minutes, service=service
        )

    subscription, invoice = paid_subscription(
        plan_registry,
        story.business,
        clock.past(-8, "09:00"),
        "flitt-demo-7781",
        "Call and message handling service — Chat, monthly",
    )
    published = request.foundation.assistant_versions[0]
    return story.finish(
        subscription=subscription,
        billing_profile=billing_details(
            story.business,
            "Studio Lindenblatt GmbH",
            "DE123456789",
            "Lindenstraße 12\n10969 Berlin",
            "buchhaltung@lindenblatt.example",
            clock.past(-9, "18:30"),
        ),
        invoices=[invoice],
        autotest_run=finished_run(
            story.business.id,
            story.published_version_id,
            clock.later(published.created_at, 12),
            build_salon_autotest_results(),
        ),
    )
