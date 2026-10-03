"""The texts of one owner's digest or monthly report."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.dto.value.value_reports import ValueReportView
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import CabinetDeepLink


class ValueDigestTextInput(ImmutableDTO):
    """A stored report in one owner's language, with the link to open it."""

    business_name: BusinessName
    language: LanguageTag
    report: ValueReportView
    link: CabinetDeepLink | None = None


class ValueDigestText(ImmutableDTO):
    """
    The report as an e-mail (`message`: the first line is the subject, the
    link line becomes a button) and as a device notification (`brief`).
    Totals only, nothing about a customer.
    """

    message: MessageText
    brief: StaffAlertBrief
