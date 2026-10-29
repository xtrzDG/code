"""Refusals of two-factor sign-in and of sensitive actions (step-up)."""

from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    AuthenticationRequiredError,
    ValidationFailedError,
)


class StepUpRequiredError(AuthenticationRequiredError):
    """
    A sensitive action needs the person to confirm it is them again (the
    session was signed in or last confirmed longer ago than
    STEP_UP_MAX_AGE_SECONDS): HTTP 401 with the reason `step_up_required`
    and `WWW-Authenticate: Bearer error="insufficient_user_authentication"`
    (RFC 9470). The session stays valid; the client confirms through
    `/v1/auth/step-up` and sends the request again.
    """


class MfaRequiredError(AccessDeniedError):
    """
    The session is signed in with the login code alone, but the platform
    admin pages, or a business that requires it of its team, take only
    sessions signed in with two factors: HTTP 403 with the reason
    `mfa_required`. The person sets up an authenticator (Account →
    Security) or signs in again with it.
    """


class WrongCodeError(ValidationFailedError):
    """
    An authenticator, recovery or confirmation code that is wrong, expired
    or already used: HTTP 422 with the reason `wrong_code`. Never 401, so a
    mistyped code while confirming an action does not end the session.
    """
