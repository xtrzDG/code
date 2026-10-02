"""Conversations of the demo restaurant in Hebrew and Arabic (right to left)."""

from app.registries.demo import demo_tool_calls as calls
from app.registries.demo.demo_activity_builder import DemoActivityBuilder
from app.registries.demo.demo_lines import assistant, customer, staff
from app.registries.demo.tbilisi_restaurant.restaurant_foundation import (
    HALL_TABLE,
    WINDOW_TABLE,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationRating
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId

HELLO_HE: str = "שלום! אני העוזר הדיגיטלי (AI) של מסעדת מצוואנה אזו."
HELLO_AR: str = "مرحبًا! أنا المساعد الذكي (AI) لمطعم متسفانه إيزو."
WHATSAPP = ChannelKind.WHATSAPP
WEB = ChannelKind.WEB_CHAT
# Closing time by weekday, Monday first (restaurant_foundation hours).
CLOSING_TIMES: tuple[str, ...] = (
    "23:00",
    "23:00",
    "23:00",
    "23:00",
    "24:00",
    "24:00",
    "22:00",
)


def record_rtl_chats(
    story: DemoActivityBuilder, guests: dict[str, ContactDocument]
) -> None:
    clock, talk, desk = story.clock, story.talk, story.desk

    # Noa books a window table for two; they came.
    start = clock.past(-9, "17:00")
    visit = clock.at(-8, "20:30")
    booking_id = BookingId()
    confirmation = "הוזמן: מחר, 20:30, שולחן ליד החלון לשניים, על שם נועה."
    chat = talk.chat(
        guests["noa"],
        WHATSAPP,
        start,
        [
            customer("שלום! אפשר שולחן לשניים מחר ב-20:30?"),
            assistant(
                f"{HELLO_HE} כן, מחר ב-20:30 יש שולחן פנוי ליד החלון. על איזה שם "
                "להזמין?",
                calls.availability(clock, desk.resource(WINDOW_TABLE), visit, 2),
            ),
            customer("נועה כהן"),
            assistant(
                f"{confirmation} נשמח לראות אתכם!",
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(WINDOW_TABLE),
                    visit,
                    2,
                    "נועה",
                    "+972501234567",
                    confirmation,
                ),
            ),
            customer("תודה רבה! 🙏"),
        ],
        rating=ConversationRating.GOOD,
        rated_by=story.owner_id,
    )
    desk.booking(
        guests["noa"],
        WINDOW_TABLE,
        visit,
        2,
        WHATSAPP,
        status=BookingStatus.COMPLETED,
        conversation=chat,
        booking_id=booking_id,
    )

    # Itay asks whether the food is kosher: recorded for the owner.
    start = clock.past(-6, "13:10")
    question_id = UnansweredQuestionId()
    question = "האם האוכל במסעדה כשר?"
    talk.chat(
        guests["itay"],
        WEB,
        start,
        [
            customer("היי, האוכל אצלכם כשר?"),
            assistant(
                f"{HELLO_HE} אין לי מידע מדויק על כשרות — העברתי את השאלה לצוות. "
                "אפשר גם להתקשר: ‎+995 32 219 00 19.",
                calls.search("כשר", [], "he"),
                calls.unanswered(question_id, question),
            ),
            customer("תודה"),
        ],
    )
    desk.question(question, "he", clock.later(start, 1), question_id=question_id)

    # Ahmad books lunch for four and asks about halal food.
    start = clock.past(-12, "15:00")
    visit = clock.at(-11, "14:00")
    booking_id, handoff_id = BookingId(), HandoffId()
    confirmation = "تم الحجز: غدًا، الساعة 14:00، طاولة لأربعة أشخاص باسم أحمد."
    summary = "الضيف يسأل عن الطعام الحلال؛ حجز غداء لأربعة أشخاص"
    chat = talk.chat(
        guests["ahmad"],
        WHATSAPP,
        start,
        [
            customer(
                "مرحبا، هل يمكن حجز طاولة لأربعة أشخاص غدًا الساعة الثانية ظهرًا؟ "
                "وهل لديكم طعام حلال؟"
            ),
            assistant(
                f"{HELLO_AR} نعم، غدًا الساعة 14:00 تتوفر طاولة لأربعة أشخاص. "
                "بخصوص الحلال، حوّلت سؤالك إلى مديرة الصالة لتجيبك بدقة. "
                "باسم من أحجز؟",
                calls.availability(clock, desk.resource(HALL_TABLE), visit, 4),
                calls.handoff(
                    handoff_id,
                    HandoffReason.NON_STANDARD_REQUEST,
                    summary,
                    HandoffUrgency.NORMAL,
                ),
            ),
            customer("أحمد"),
            assistant(
                confirmation,
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(HALL_TABLE),
                    visit,
                    4,
                    "أحمد",
                    "+971501234567",
                    confirmation,
                ),
            ),
            staff(
                "مرحبًا أحمد، أنا تمار مديرة الصالة. اللحوم لدينا غير معتمدة كحلال، "
                "وبعض الأطباق تحتوي على لحم الخنزير. لدينا أطباق نباتية كثيرة: "
                "لوبيو، بخالي، خاتشابوري. أهلًا بكم!",
                pause=1200,
            ),
            customer("شكرًا جزيلًا", pause=300),
        ],
    )
    desk.booking(
        guests["ahmad"],
        HALL_TABLE,
        visit,
        4,
        WHATSAPP,
        status=BookingStatus.COMPLETED,
        conversation=chat,
        booking_id=booking_id,
    )
    desk.handoff(
        chat,
        HandoffReason.NON_STANDARD_REQUEST,
        summary,
        HandoffUrgency.NORMAL,
        resolved_after_minutes=20,
        handoff_id=handoff_id,
    )

    # Layla asks about tonight's hours and live music.
    start = clock.past(-3, "20:15")
    closing: str = CLOSING_TIMES[clock.weekday_index(start)]
    talk.chat(
        guests["layla"],
        WEB,
        start,
        [
            customer("مساء الخير، حتى أي ساعة تفتحون اليوم؟ وهل توجد موسيقى حية؟"),
            assistant(
                "مساء الخير! أنا المساعد الذكي (AI) لمطعم متسفانه إيزو. نعمل اليوم "
                f"حتى الساعة {closing}. الموسيقى الحية أيام الجمعة والسبت من الساعة "
                "20:00: غيتار وغناء جورجي متعدد الأصوات.",
                calls.search("موسيقى حية", [story.item("Когда у вас живая")], "ar"),
            ),
        ],
    )
