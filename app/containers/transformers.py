from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.utilities import UtilitiesContainer
from app.transformers.assembly.assistant_instruction_transformer import (
    AssistantInstructionTransformer,
)
from app.transformers.assembly.assistant_version_details_transformer import (
    AssistantVersionDetailsTransformer,
)
from app.transformers.assembly.assistant_version_summary_transformer import (
    AssistantVersionSummaryTransformer,
)
from app.transformers.assembly.autotest_run_view_transformer import (
    AutotestRunViewTransformer,
)
from app.transformers.assembly.business_facts_transformer import (
    BusinessFactsTransformer,
)
from app.transformers.assembly.phone_instruction_transformer import (
    PhoneInstructionTransformer,
)
from app.transformers.billing.billing_notice_transformer import (
    BillingNoticeTransformer,
)
from app.transformers.billing.invoice_description_transformer import (
    InvoiceDescriptionTransformer,
)
from app.transformers.businesses.business_view_transformer import (
    BusinessViewTransformer,
)
from app.transformers.conversations.call_view_transformer import (
    CallViewTransformer,
)
from app.transformers.conversations.conversation_summary_transformer import (
    ConversationSummaryTransformer,
)
from app.transformers.conversations.message_view_transformer import (
    MessageViewTransformer,
)
from app.transformers.inbox.inbox_item_transformer import InboxItemTransformer
from app.transformers.notifications.booking_cancelled_notification_transformer import (  # noqa: E501
    BookingCancelledNotificationTransformer,
)
from app.transformers.notifications.booking_confirmation_transformer import (
    BookingConfirmationTransformer,
)
from app.transformers.notifications.booking_moved_notification_transformer import (
    BookingMovedNotificationTransformer,
)
from app.transformers.notifications.booking_reminder_template_transformer import (
    BookingReminderTemplateTransformer,
)
from app.transformers.notifications.booking_reminder_transformer import (
    BookingReminderTransformer,
)
from app.transformers.notifications.calendar_event_text_transformer import (
    CalendarEventTextTransformer,
)
from app.transformers.notifications.call_report_brief_transformer import (
    CallReportBriefTransformer,
)
from app.transformers.notifications.call_report_text_transformer import (
    CallReportTextTransformer,
)
from app.transformers.notifications.cancellation_confirmation_transformer import (
    CancellationConfirmationTransformer,
)
from app.transformers.notifications.handoff_customer_message_transformer import (
    HandoffCustomerMessageTransformer,
)
from app.transformers.notifications.handoff_notification_transformer import (
    HandoffNotificationTransformer,
)
from app.transformers.notifications.handoff_summary_transformer import (
    HandoffSummaryTransformer,
)
from app.transformers.notifications.new_booking_notification_transformer import (
    NewBookingNotificationTransformer,
)
from app.transformers.notifications.new_lead_notification_transformer import (
    NewLeadNotificationTransformer,
)
from app.transformers.notifications.reschedule_confirmation_transformer import (
    RescheduleConfirmationTransformer,
)
from app.transformers.notifications.staff_alert_brief_transformer import (
    StaffAlertBriefTransformer,
)
from app.transformers.notifications.staff_notification_text_transformer import (
    StaffNotificationTextTransformer,
)
from app.transformers.users.user_view_transformer import UserViewTransformer


class TransformersContainer(containers.DeclarativeContainer):
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Accounts.
    user_view_transformer: Singleton[UserViewTransformer] = Singleton(
        UserViewTransformer
    )
    business_view_transformer: Singleton[BusinessViewTransformer] = Singleton(
        BusinessViewTransformer
    )

    # --- Assembly and autotests.
    business_facts_transformer: Singleton[BusinessFactsTransformer] = Singleton(
        BusinessFactsTransformer
    )
    assistant_instruction_transformer: Singleton[AssistantInstructionTransformer] = (
        Singleton(AssistantInstructionTransformer)
    )
    phone_instruction_transformer: Singleton[PhoneInstructionTransformer] = Singleton(
        PhoneInstructionTransformer
    )
    assistant_version_details_transformer: Singleton[
        AssistantVersionDetailsTransformer
    ] = Singleton(AssistantVersionDetailsTransformer)
    assistant_version_summary_transformer: Singleton[
        AssistantVersionSummaryTransformer
    ] = Singleton(AssistantVersionSummaryTransformer)
    autotest_run_view_transformer: Singleton[AutotestRunViewTransformer] = Singleton(
        AutotestRunViewTransformer
    )

    # --- Conversation feed.
    conversation_summary_transformer: Singleton[ConversationSummaryTransformer] = (
        Singleton(ConversationSummaryTransformer)
    )
    call_view_transformer: Singleton[CallViewTransformer] = Singleton(
        CallViewTransformer
    )
    message_view_transformer: Singleton[MessageViewTransformer] = Singleton(
        MessageViewTransformer
    )
    # The team inbox's staff-safe rows.
    inbox_item_transformer: Singleton[InboxItemTransformer] = Singleton(
        InboxItemTransformer
    )

    # --- Billing texts.
    invoice_description_transformer: Singleton[InvoiceDescriptionTransformer] = (
        Singleton(
            InvoiceDescriptionTransformer,
            localized_text_resolver=utilities.localized_text_resolver,
        )
    )
    billing_notice_transformer: Singleton[BillingNoticeTransformer] = Singleton(
        BillingNoticeTransformer,
        localized_text_resolver=utilities.localized_text_resolver,
    )

    # --- Customer and staff messages about bookings, leads and handoffs.
    booking_confirmation_transformer: Singleton[BookingConfirmationTransformer] = (
        Singleton(
            BookingConfirmationTransformer,
            text_resolver=utilities.localized_text_resolver,
        )
    )
    cancellation_confirmation_transformer: Singleton[
        CancellationConfirmationTransformer
    ] = Singleton(
        CancellationConfirmationTransformer,
        text_resolver=utilities.localized_text_resolver,
    )
    reschedule_confirmation_transformer: Singleton[
        RescheduleConfirmationTransformer
    ] = Singleton(
        RescheduleConfirmationTransformer,
        text_resolver=utilities.localized_text_resolver,
    )
    booking_reminder_transformer: Singleton[BookingReminderTransformer] = Singleton(
        BookingReminderTransformer,
        text_resolver=utilities.localized_text_resolver,
    )
    booking_reminder_template_transformer: Singleton[
        BookingReminderTemplateTransformer
    ] = Singleton(BookingReminderTemplateTransformer)
    new_booking_notification_transformer: Singleton[
        NewBookingNotificationTransformer
    ] = Singleton(
        NewBookingNotificationTransformer,
        text_resolver=utilities.localized_text_resolver,
    )
    booking_cancelled_notification_transformer: Singleton[
        BookingCancelledNotificationTransformer
    ] = Singleton(
        BookingCancelledNotificationTransformer,
        text_resolver=utilities.localized_text_resolver,
    )
    booking_moved_notification_transformer: Singleton[
        BookingMovedNotificationTransformer
    ] = Singleton(
        BookingMovedNotificationTransformer,
        text_resolver=utilities.localized_text_resolver,
    )
    new_lead_notification_transformer: Singleton[NewLeadNotificationTransformer] = (
        Singleton(
            NewLeadNotificationTransformer,
            text_resolver=utilities.localized_text_resolver,
        )
    )
    handoff_notification_transformer: Singleton[HandoffNotificationTransformer] = (
        Singleton(
            HandoffNotificationTransformer,
            text_resolver=utilities.localized_text_resolver,
        )
    )
    handoff_summary_transformer: Singleton[HandoffSummaryTransformer] = Singleton(
        HandoffSummaryTransformer,
        text_resolver=utilities.localized_text_resolver,
    )
    handoff_customer_message_transformer: Singleton[
        HandoffCustomerMessageTransformer
    ] = Singleton(
        HandoffCustomerMessageTransformer,
        text_resolver=utilities.localized_text_resolver,
    )
    calendar_event_text_transformer: Singleton[CalendarEventTextTransformer] = (
        Singleton(
            CalendarEventTextTransformer,
            text_resolver=utilities.localized_text_resolver,
        )
    )
    # Staff alerts: the brief of e-mail, SMS and devices (no customer
    # details) and the text each recipient gets, with its link.
    staff_alert_brief_transformer: Singleton[StaffAlertBriefTransformer] = Singleton(
        StaffAlertBriefTransformer,
        text_resolver=utilities.localized_text_resolver,
    )
    staff_notification_text_transformer: Singleton[StaffNotificationTextTransformer] = (
        Singleton(
            StaffNotificationTextTransformer,
            text_resolver=utilities.localized_text_resolver,
        )
    )
    # Staff texts about calls: the summary after a call and the note about a
    # caller who did not get through (detailed, and brief without details).
    call_report_text_transformer: Singleton[CallReportTextTransformer] = Singleton(
        CallReportTextTransformer, text_resolver=utilities.localized_text_resolver
    )
    call_report_brief_transformer: Singleton[CallReportBriefTransformer] = Singleton(
        CallReportBriefTransformer, text_resolver=utilities.localized_text_resolver
    )
