"""
Staff notifications: alerts to every recipient of a business, the queue of
device notifications, their sender, and the record of how delivery went.
"""

from typing import Protocol

from app.contracts.base_contract import BaseContract
from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.outbound_messages import (
    OutboundMessageDocument,
    PushRecipient,
)
from app.schemas.dto.notifications.staff_alerts import (
    PushNotification,
    StaffAlert,
    StaffAlertBrief,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag


class StaffAlertTextsContract(BaseContract, Protocol):
    """The texts of one alert, rendered on demand in any language."""

    def detailed(self, language: LanguageTag) -> MessageText:
        """For chats the staff member linked (Telegram, WhatsApp)."""
        raise NotImplementedError

    def brief(self, language: LanguageTag) -> StaffAlertBrief:
        """For e-mail, SMS and devices: nothing about the customer."""
        raise NotImplementedError


class StaffAlertFacilitatorContract(FacilitatorContract, Protocol):
    def alert(
        self,
        business: BusinessDocument,
        alert: StaffAlert,
        texts: StaffAlertTextsContract,
    ) -> DeliveredNotificationCount:
        """
        Queue the alert for every staff contact and every subscribed device
        that wants this event, each in its language with a signed link,
        held through their quiet hours unless urgent. Returns how many were
        queued for delivery. Never raises.
        """
        raise NotImplementedError


class PushNotificationQueueContract(FacilitatorContract, Protocol):
    def queue(self, notification: PushNotification) -> bool:
        """
        Queue a device notification in the outbox; False when it cannot be
        delivered (push is not configured, too many for this device) or
        could not be queued. Never raises.
        """
        raise NotImplementedError


class PushNotificationSenderContract(FacilitatorContract, Protocol):
    def send(
        self,
        business_id: BusinessId,
        recipient: PushRecipient,
        body: MessageText,
    ) -> None:
        """
        Send one device notification. A device the push service no longer
        knows is deleted (PushSubscriptionGoneError). Raises
        DeliveryNotConfiguredError, ProviderRateLimitedError,
        ProviderRejectedMessageError or ExternalServiceError.
        """
        raise NotImplementedError


class StaffDeliveryRecorderContract(FacilitatorContract, Protocol):
    def record(self, message: OutboundMessageDocument) -> None:
        """
        Note how a staff notification stands (sending, delivered, failed
        with its reason) on its contact's delivery state or its device.
        Ignores other messages; never raises.
        """
        raise NotImplementedError
