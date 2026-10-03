"""Refusals of login code requests by the abuse protection."""

from collections.abc import Sequence

from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.login_protection import LoginCodeCapAlert
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    RateLimitedError,
)


class BotCheckRequiredError(AccessDeniedError):
    """
    A risky login code request needs a passed bot check (Cloudflare
    Turnstile) first: HTTP 403 whose reason `challenge_required` carries the
    widget's site key in its details. The client shows the check and sends
    the request again with its token.
    """


class LoginCodeCapReachedError(RateLimitedError):
    """
    A platform cap of login code sends (per country, new destinations or
    verified users) refused the send: HTTP 429, and the platform team is
    alerted with `alert`.
    """

    def __init__(
        self,
        *args: object,
        alert: LoginCodeCapAlert,
        reasons: Sequence[ErrorReason] = (),
    ) -> None:
        super().__init__(*args, reasons=reasons)
        self.alert: LoginCodeCapAlert = alert
