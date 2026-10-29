"""Contracts of the subscription lifecycle: its rules and the win-back messages."""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.registry_contract import RegistryContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.subscription_lifecycle_policy import SubscriptionLifecyclePolicy
from app.schemas.dto.win_back_messages import WinBackMessage
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    WinBackRecipientCount,
)


class SubscriptionLifecyclePolicyRegistryContract(RegistryContract, Protocol):
    def policy(self) -> SubscriptionLifecyclePolicy:
        """The pause price and cap, the offers per reason, the win-back days."""
        raise NotImplementedError


class OwnerWinBackFacilitatorContract(FacilitatorContract, Protocol):
    def send(
        self,
        business: BusinessDocument,
        message: WinBackMessage,
    ) -> WinBackRecipientCount:
        """
        Queue the message in the outbox for every owner (their sign-in
        e-mail, or WhatsApp for an owner who signed in by phone) and the
        business's Telegram chats linked to the platform bot, each in its
        language, with a signed link to the billing page; each address
        gets a stage once however often it is queued. Returns how many were
        queued. Never raises.
        """
        raise NotImplementedError
