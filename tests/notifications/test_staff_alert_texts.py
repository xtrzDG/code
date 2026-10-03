"""Brief staff texts: a title and one line in the recipient's language."""

from app.schemas.constants.bookings import LeadType
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.constants.notifications import StaffTextStyle
from app.schemas.dto.notifications.staff_alerts import (
    HandoffBrief,
    LeadBrief,
    StaffAlertBrief,
    StaffAlertBriefInput,
    StaffNotificationTextInput,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import CabinetDeepLink
from app.transformers.notifications.staff_alert_brief_transformer import (
    StaffAlertBriefTransformer,
)
from app.transformers.notifications.staff_notification_text_transformer import (
    StaffNotificationTextTransformer,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver

BUSINESS = BusinessName("Salobie Bia")
LINK = CabinetDeepLink("https://cabinet.example.com/n/" + "A" * 67)


def brief(language: str, **facts: object) -> StaffAlertBrief:
    return StaffAlertBriefTransformer(LocalizedTextResolver()).transform(
        StaffAlertBriefInput.model_validate(
            {"business_name": BUSINESS, "language": LanguageTag(language), **facts}
        )
    )


def test_handoffs_say_how_urgent_they_are_without_customer_details() -> None:
    urgent = brief(
        "ka",
        handoff=HandoffBrief(
            reason=HandoffReason.COMPLAINT, urgency=HandoffUrgency.CRITICAL
        ),
    )
    normal = brief(
        "ru",
        handoff=HandoffBrief(
            reason=HandoffReason.CUSTOMER_REQUEST, urgency=HandoffUrgency.NORMAL
        ),
    )

    assert str(urgent.title).startswith("სასწრაფო")
    assert str(urgent.detail).startswith("Salobie Bia · ")
    assert not str(normal.title).startswith("Срочно")
    assert str(normal.detail).startswith("Salobie Bia · ")


def test_requests_name_their_kind_and_date_and_tests_say_what_comes() -> None:
    dated = brief(
        "en",
        lead=LeadBrief(
            lead_type=LeadType.BANQUET, requested_date=LocalDate("2026-10-10")
        ),
    )
    undated = brief("en", lead=LeadBrief(lead_type=LeadType.ORDER))
    check = brief("ru")

    assert "Salobie Bia" in str(dated.title)
    assert "10" in str(dated.detail)
    assert undated.detail is not None and "·" not in str(undated.detail)
    assert str(check.title) == "Проверка уведомлений · Salobie Bia"
    assert str(check.detail) == "Сюда будут приходить передачи, заявки и брони."


def text(style: StaffTextStyle, language: str, link: CabinetDeepLink | None) -> str:
    return str(
        StaffNotificationTextTransformer(LocalizedTextResolver()).transform(
            StaffNotificationTextInput(
                style=style,
                language=LanguageTag(language),
                detailed=MessageText("Nino: tooth hurts, +995 555 12 34 56"),
                brief=brief(language),
                link=link,
            )
        )
    )


def test_each_text_ends_with_the_link_in_the_recipients_language() -> None:
    assert text(StaffTextStyle.DETAILED, "ka", LINK) == (
        f"Nino: tooth hurts, +995 555 12 34 56\nგახსნა: {LINK}"
    )
    assert text(StaffTextStyle.BRIEF, "en", LINK) == (
        "Test notification · Salobie Bia\n"
        "Handoffs, requests and bookings will arrive here.\n"
        f"Open: {LINK}"
    )
    assert text(StaffTextStyle.BRIEF, "de", None).startswith("Test notification")
    assert "+995" not in text(StaffTextStyle.BRIEF, "ru", LINK)
