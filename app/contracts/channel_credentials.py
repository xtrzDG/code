"""Asking Meta about the access tokens of connected channels."""

from typing import Protocol

from app.contracts.channel_clients import ProviderToken
from app.contracts.client_contract import ClientContract
from app.schemas.dto.channels.credential_inspection import MetaTokenFacts
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret


class MetaTokenDebugClientContract(ClientContract, Protocol):
    """Graph API `debug_token`, asked with the platform's Meta app."""

    def inspect_token(
        self,
        token: ProviderToken,
        app_id: PlatformIdentifier,
        app_secret: PlatformSecret,
    ) -> MetaTokenFacts:
        """
        What Meta says of the token. Raises ExternalServiceError when Meta
        cannot be asked, ValidationFailedError when it refuses the app.
        """
        raise NotImplementedError
