import logging

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.operations import ManagerBroadcastFacilitatorContract
from app.schemas.dto.operations import StaffMessage
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)

LOGGER: logging.Logger = logging.getLogger(__name__)


class ManagerBroadcastFacilitator(ManagerBroadcastFacilitatorContract):
    """
    Sends staff messages one by one through the manager notifier (platform
    Telegram bot, WhatsApp template, e-mail or SMS).

    A notifier that fails or even raises for one contact never stops the
    others and never breaks the booking, lead or handoff being notified about.
    """

    def __init__(self, notifier: ManagerNotificationFacilitatorContract) -> None:
        self._notifier: ManagerNotificationFacilitatorContract = notifier

    def broadcast(self, messages: list[StaffMessage]) -> DeliveredNotificationCount:
        delivered: int = 0
        for message in messages:
            try:
                is_delivered: bool = self._notifier.notify(
                    message.contact, message.text
                )
            except Exception:  # noqa: BLE001 - notifier must never break the action
                LOGGER.exception(
                    "Staff notification via %s raised.", message.contact.channel
                )
                continue

            if is_delivered:
                delivered += 1
            else:
                LOGGER.warning(
                    "Staff notification via %s was not delivered.",
                    message.contact.channel,
                )

        return DeliveredNotificationCount(delivered)
