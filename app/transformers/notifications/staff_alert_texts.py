"""
Localized templates of the brief staff alerts (e-mail, SMS, devices) and of
the link line every staff notification ends with. Brief texts say what
happened and where, never who the customer is.
"""

from collections.abc import Mapping

from app.schemas.constants.notifications import StaffBookingChange
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.owner_texts import owner_text

HANDOFF_TITLE: LocalizedText = owner_text("notifications.staff_alert.handoff_title")
URGENT_HANDOFF_TITLE: LocalizedText = owner_text(
    "notifications.staff_alert.urgent_handoff_title"
)
HANDOFF_DETAIL: LocalizedText = owner_text("notifications.staff_alert.handoff_detail")
LEAD_TITLE: LocalizedText = owner_text("notifications.staff_alert.lead_title")
LEAD_DETAIL_WITH_DATE: LocalizedText = owner_text(
    "notifications.staff_alert.lead_detail_with_date"
)
BOOKING_TITLES: Mapping[StaffBookingChange, LocalizedText] = {
    StaffBookingChange.CREATED: owner_text(
        "notifications.staff_alert.booking_titles.created"
    ),
    StaffBookingChange.MOVED: owner_text(
        "notifications.staff_alert.booking_titles.moved"
    ),
    StaffBookingChange.CANCELLED: owner_text(
        "notifications.staff_alert.booking_titles.cancelled"
    ),
}
BOOKING_DETAIL: LocalizedText = owner_text("notifications.staff_alert.booking_detail")
LINK_LINE: LocalizedText = owner_text("notifications.staff_alert.link_line")
TEST_TITLE: LocalizedText = owner_text("notifications.staff_alert.test_title")
TEST_DETAIL: LocalizedText = owner_text("notifications.staff_alert.test_detail")
