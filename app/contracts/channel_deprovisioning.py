"""Switching a closed business's channels off at their providers."""

from typing import Protocol

from app.contracts.channel_clients import ProviderToken
from app.contracts.client_contract import ClientContract
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
)


class MetaSubscriptionClientContract(ClientContract, Protocol):
    """
    The platform app's webhook subscriptions at Meta, taken back when a
    business is deleted. Errors: ExternalServiceError when Meta cannot be
    asked, ValidationFailedError when it refuses the token.
    """

    def unsubscribe_page(self, page_token: ProviderToken) -> None:
        """
        The page the token belongs to (its Messenger and its Instagram
        account) stops sending the app its messages.
        """
        raise NotImplementedError

    def unsubscribe_whatsapp_business_account(
        self,
        access_token: ProviderToken,
        business_account_id: WhatsAppBusinessAccountId,
    ) -> None:
        """The business's own WhatsApp account stops sending the app its messages."""
        raise NotImplementedError
