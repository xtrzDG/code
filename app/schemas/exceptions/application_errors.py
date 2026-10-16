"""Application error hierarchy.

Gateways map these classes to transport status codes in one place; business
code raises the most specific class and never builds transport responses.
"""

from collections.abc import Sequence

from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds


class NotFoundError(ApplicationError):
    """Requested entity does not exist or is not visible to the caller."""


class ValidationFailedError(ApplicationError):
    """Input is well-formed but violates a business rule."""


class ConflictError(ApplicationError):
    """Action conflicts with current state (slot taken, already active)."""


class PreconditionFailedError(ApplicationError):
    """
    The request's precondition (an If-Match header) does not hold: what it
    names was changed since the caller read it.
    """


class AuthenticationRequiredError(ApplicationError):
    """Caller is not authenticated or the credentials are invalid or expired."""


class AccessDeniedError(ApplicationError):
    """Caller is authenticated but may not perform the action."""


class RateLimitedError(ApplicationError):
    """
    Too many attempts (wrong one-time codes, repeated requests).

    `retry_after_seconds`, when known, becomes the response's Retry-After
    header.
    """

    def __init__(
        self,
        *args: object,
        reasons: Sequence[ErrorReason] = (),
        retry_after_seconds: RetryAfterSeconds | None = None,
    ) -> None:
        super().__init__(*args, reasons=reasons)
        self.retry_after_seconds: RetryAfterSeconds | None = retry_after_seconds


class ExternalServiceError(ApplicationError):
    """A provider (LLM, messaging, telephony) failed or is unavailable."""


class ChannelCredentialRejectedError(ExternalServiceError):
    """
    A messaging platform refused a business's channel credential (a revoked
    bot token, an expired page token, lost permissions): the channel stops
    working until the owner reconnects it.
    """


class ProviderRateLimitedError(ExternalServiceError):
    """
    A messaging platform asked to slow down (HTTP 429, Telegram
    `retry_after`, Meta throttling codes). Sending again after
    `retry_after_seconds` (when the platform named it) can succeed.
    """

    def __init__(
        self,
        *args: object,
        retry_after_seconds: RetryAfterSeconds | None = None,
    ) -> None:
        super().__init__(*args)
        self.retry_after_seconds: RetryAfterSeconds | None = retry_after_seconds


class ProviderRejectedMessageError(ExternalServiceError):
    """
    A messaging platform refused this message for good (a 4xx other than a
    rate limit: the customer blocked the bot, the recipient does not exist,
    the 24-hour window is closed). Sending the same message again cannot
    help.
    """


class DeliveryNotConfiguredError(ExternalServiceError):
    """
    No provider is configured for this kind of message (staff e-mail or SMS
    in production, the platform bot or WhatsApp template not set up).
    """


class WhatsAppTemplateRejectedError(ExternalServiceError):
    """
    Meta refused a WhatsApp message template: no approved template has that
    name in that language, or its variables do not match. Trying again
    cannot help until the template setting is corrected.
    """


class InvalidPhoneNumberError(ValidationFailedError):
    """Text is not a valid phone number for the given or detected country."""


class UnknownCountryError(ValidationFailedError):
    """Country code is not an ISO 3166-1 alpha-2 code known to the registry."""


class CountryRestrictedError(AccessDeniedError):
    """Businesses from this country cannot be onboarded."""


class UnsupportedLanguageError(ValidationFailedError):
    """Language tag is not usable for the requested purpose."""


class LlmRefusedError(ExternalServiceError):
    """The language model declined the request and no fallback answered."""
