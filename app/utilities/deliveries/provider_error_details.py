"""
The raw error texts providers answered (a messenger's, an SMS or e-mail
service's, a push service's own words) are platform details (OWASP API3,
ASVS V15.3.1, API-05): only platform admins get them. The team of a
business keeps the plain state (failed, retrying, `is_last_delivery_failed`)
and, where there is one, the reason in the cabinet's terms
(`last_error_reason` of a channel), as conversations keep their tool calls
without inputs and results (`app/utilities/conversations/platform_details.py`).
Each function is the answer of one endpoint as the team sees it
(`TeamViewOrchestrator`).
"""

from app.schemas.dto.calls.call_settings import TextBackPage
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.feedback.feedback_requests import FeedbackRequestPage
from app.schemas.dto.notifications.notification_settings import (
    MyNotificationSettingsView,
    NotificationCheckResult,
    NotificationContactList,
    PushDeviceView,
    StaffDeliveryView,
)

WITHOUT_ERROR: dict[str, None] = {"last_error": None}


def team_text_backs(page: TextBackPage) -> TextBackPage:
    return page.model_copy(
        update={"items": [item.model_copy(update=WITHOUT_ERROR) for item in page.items]}
    )


def team_feedback_requests(page: FeedbackRequestPage) -> FeedbackRequestPage:
    return page.model_copy(
        update={"items": [item.model_copy(update=WITHOUT_ERROR) for item in page.items]}
    )


def team_delivery(delivery: StaffDeliveryView) -> StaffDeliveryView:
    return delivery.model_copy(update=WITHOUT_ERROR)


def team_notification_contacts(
    contacts: NotificationContactList,
) -> NotificationContactList:
    return contacts.model_copy(
        update={
            "items": [
                contact
                if contact.delivery is None
                else contact.model_copy(
                    update={"delivery": team_delivery(contact.delivery)}
                )
                for contact in contacts.items
            ]
        }
    )


def team_notification_check(result: NotificationCheckResult) -> NotificationCheckResult:
    return result.model_copy(update={"delivery": team_delivery(result.delivery)})


def team_device(device: PushDeviceView) -> PushDeviceView:
    return device.model_copy(update=WITHOUT_ERROR)


def team_notification_settings(
    settings: MyNotificationSettingsView,
) -> MyNotificationSettingsView:
    return settings.model_copy(
        update={"devices": [team_device(device) for device in settings.devices]}
    )


def team_channel(channel: ChannelView) -> ChannelView:
    """A channel without the provider's words; `last_error_reason` stays."""

    return channel.model_copy(update=WITHOUT_ERROR)


def team_channels(channels: list[ChannelView]) -> list[ChannelView]:
    return [team_channel(channel) for channel in channels]
