"""Application error hierarchy.

Gateways map these classes to transport status codes in one place; business
code raises the most specific class and never builds transport responses.
"""

from app.schemas.exceptions.base_exception import ApplicationError


class NotFoundError(ApplicationError):
    """Requested entity does not exist or is not visible to the caller."""


class ValidationFailedError(ApplicationError):
    """Input is well-formed but violates a business rule."""


class ConflictError(ApplicationError):
    """Action conflicts with current state (slot taken, already active)."""


class AuthenticationRequiredError(ApplicationError):
    """Caller is not authenticated or the credentials are invalid or expired."""


class AccessDeniedError(ApplicationError):
    """Caller is authenticated but may not perform the action."""


class RateLimitedError(ApplicationError):
    """Too many attempts (wrong one-time codes, repeated requests)."""


class ExternalServiceError(ApplicationError):
    """A provider (LLM, messaging, telephony) failed or is unavailable."""


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
