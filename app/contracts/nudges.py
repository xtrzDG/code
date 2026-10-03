"""Contracts of the activation follow-up: delivering a nudge to the owners."""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.setup.nudges import NudgeMessage
from app.schemas.typings.setup.constrained_integers import NudgeRecipientCount


class OwnerNudgeFacilitatorContract(FacilitatorContract, Protocol):
    def send(
        self,
        business: BusinessDocument,
        nudge: NudgeMessage,
    ) -> NudgeRecipientCount:
        """
        Queue the nudge in the outbox for the owners' e-mail addresses and
        devices and the business's Telegram chats linked to the platform
        bot, each in its language, with a signed link to the cabinet page;
        each address gets it once however often it is queued. Returns how
        many were queued. Never raises.
        """
        raise NotImplementedError
