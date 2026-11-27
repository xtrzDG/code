"""
Asking Meta about the access tokens of connected channels, renewing the
WhatsApp Embedded Signup ones, and finding the tokens that end soon.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.channel_clients import ProviderToken
from app.contracts.client_contract import ClientContract
from app.contracts.repo_contract import RepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels.credential_inspection import MetaTokenFacts
from app.schemas.dto.channels.meta_provider import MetaAppCredentials
from app.schemas.typings.meta_connection.strings import MetaAccessToken
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit


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


class MetaTokenRefreshClientContract(ClientContract, Protocol):
    """
    Meta's renewal of an expiring system user token, in the name of the
    platform's Meta app: the business's own token of WhatsApp Embedded
    Signup (60 days) traded for a new one that runs 60 days from now. The
    old token keeps working until its own end.
    """

    def refresh_business_token(
        self, token: MetaAccessToken, app: MetaAppCredentials
    ) -> MetaAccessToken:
        """
        The new token (its end comes from `debug_token`, not this answer).

        Raises:
            ValidationFailedError: Meta refused the token or the app.
            ChannelCredentialRejectedError: Meta rejected the token (401, 403).
            ProviderRejectedMessageError: Meta refused the request otherwise.
            ProviderRateLimitedError: Meta asked to slow down.
            ExternalServiceError: Meta could not be asked, or answered
                without a token.
        """
        raise NotImplementedError


class ChannelCredentialWatchRepoContract(RepoContract, Protocol):
    """The channels whose Meta tokens end soon or ended, across every business."""

    def list_active_credentials_ending_before(
        self,
        kind: ChannelKind,
        ending_before: Microseconds,
        in_error_ending_from: Microseconds,
        limit: DocumentQueryLimit,
    ) -> list[ChannelDocument]:
        """
        Channels of the kind whose token ends before `ending_before`
        (exclusive), soonest first, at most `limit` of them: every connected
        one, however long ago its token ended, and those in ERROR whose
        token ends at `in_error_ending_from` or later. Switched-off channels
        and tokens without an end are never listed.
        """
        raise NotImplementedError
