"""
Meta's self-serve connection: the Facebook sign-ins started on the Channels
page, and the Graph API calls that turn one into a connected channel
(WhatsApp Embedded Signup, the page picker, Instagram's private replies).
"""

from collections.abc import Callable
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.client_contract import ClientContract
from app.contracts.repo_contract import RepoContract
from app.schemas.domain.meta_connections import MetaConnectionStateDocument
from app.schemas.dto.channels.meta_provider import (
    MetaAppCredentials,
    MetaPageChoice,
    MetaTokenGrants,
)
from app.schemas.dto.channels.provider_profiles import WhatsAppPhoneNumberProfile
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import MetaObjectId
from app.schemas.typings.channels.strings import ChannelSecret, ProviderMessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaCommentId,
    MetaConnectionStateHash,
    MetaEmbeddedSignupCode,
    MetaLoginCode,
    WhatsAppBusinessAccountId,
    WhatsAppRegistrationPin,
)
from app.schemas.typings.meta_connection.strings import (
    MetaAccessToken,
    MetaPageAccessToken,
)
from app.schemas.typings.storage.constrained_integers import DocumentCount

type MetaConnectionStateChange = Callable[
    [MetaConnectionStateDocument], MetaConnectionStateDocument | None
]


class MetaConnectionStateRepoContract(RepoContract, Protocol):
    """
    The Facebook sign-ins of a business, each under the hash of its state
    and read only inside the business that started it.
    """

    def save(self, state: MetaConnectionStateDocument) -> None:
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, state_hash: MetaConnectionStateHash
    ) -> MetaConnectionStateDocument | None:
        raise NotImplementedError

    def modify(
        self,
        business_id: BusinessId,
        state_hash: MetaConnectionStateHash,
        change: MetaConnectionStateChange,
    ) -> MetaConnectionStateDocument | None:
        """
        Apply `change` to the business's stored sign-in in one step (no other
        write in between); what was written, None when it is missing,
        another business's, or `change` declined.
        """
        raise NotImplementedError

    def list_of_business(
        self, business_id: BusinessId
    ) -> list[MetaConnectionStateDocument]:
        """Every sign-in the business's owners started and nobody removed."""
        raise NotImplementedError

    def delete(
        self, business_id: BusinessId, state_hash: MetaConnectionStateHash
    ) -> None:
        raise NotImplementedError

    def delete_ended_before(self, moment: Microseconds) -> DocumentCount:
        """
        Across businesses: delete the sign-ins that ended before `moment`
        (an abandoned page picker's kept token with them); how many.
        """
        raise NotImplementedError


class MetaOAuthClientContract(ClientContract, Protocol):
    """
    Facebook Login's server side: codes exchanged for tokens and the
    permissions a token holds, in the name of the platform's Meta app.
    Errors: ValidationFailedError when Meta refuses the code or token,
    ExternalServiceError when it cannot be asked.
    """

    def exchange_code(
        self,
        code: MetaEmbeddedSignupCode | MetaLoginCode,
        app: MetaAppCredentials,
    ) -> MetaAccessToken:
        """The token of a code the cabinet's Facebook SDK received."""
        raise NotImplementedError

    def extend_user_token(
        self, token: MetaAccessToken, app: MetaAppCredentials
    ) -> MetaAccessToken:
        """A person's short-lived token traded for a long-lived one."""
        raise NotImplementedError

    def read_grants(
        self, token: MetaAccessToken, app: MetaAppCredentials
    ) -> MetaTokenGrants:
        """`debug_token`: the permissions (with granular targets) it holds."""
        raise NotImplementedError


class MetaPagesClientContract(ClientContract, Protocol):
    """The pages a signed-in person manages, and the token of one of them."""

    def list_pages(
        self, user_token: MetaAccessToken, app: MetaAppCredentials
    ) -> list[MetaPageChoice]:
        raise NotImplementedError

    def read_page_token(
        self,
        user_token: MetaAccessToken,
        page_id: MetaObjectId,
        app: MetaAppCredentials,
    ) -> MetaPageAccessToken | None:
        """None when the person cannot act for the page (no token offered)."""
        raise NotImplementedError


class WhatsAppOnboardingClientContract(ClientContract, Protocol):
    """
    The Cloud API steps after Embedded Signup, with the business's own
    token: its numbers, the app's webhooks on its account, and the number's
    registration.
    """

    def list_phone_numbers(
        self,
        business_token: MetaAccessToken,
        account_id: WhatsAppBusinessAccountId,
        app: MetaAppCredentials,
    ) -> list[WhatsAppPhoneNumberProfile]:
        raise NotImplementedError

    def subscribe_app(
        self,
        business_token: MetaAccessToken,
        account_id: WhatsAppBusinessAccountId,
        app: MetaAppCredentials,
    ) -> None:
        raise NotImplementedError

    def register_number(
        self,
        business_token: MetaAccessToken,
        phone_number_id: MetaObjectId,
        pin: WhatsAppRegistrationPin,
        app: MetaAppCredentials,
    ) -> None:
        """
        Register the number for the Cloud API with its two-step PIN; a
        number registered before with another PIN raises
        WhatsAppPinMismatchError.
        """
        raise NotImplementedError


class MetaPrivateReplyClientContract(ClientContract, Protocol):
    """Instagram's private replies: one message to a comment's author."""

    def send_private_reply(
        self,
        page_token: ChannelSecret,
        comment_id: MetaCommentId,
        text: MessageText,
    ) -> ProviderMessageId | None:
        """
        The sent message's id. Errors as a page message's (a comment already
        answered or older than seven days is refused for good).
        """
        raise NotImplementedError
