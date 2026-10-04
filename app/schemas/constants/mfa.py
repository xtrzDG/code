from enum import StrEnum


class AuthLevel(StrEnum):
    """
    How a session was signed in: with the login code alone (ONE_FACTOR) or
    with the login code and an authenticator or recovery code (TWO_FACTOR).
    Platform admin pages and businesses that require it take only
    TWO_FACTOR sessions.
    """

    ONE_FACTOR = "one_factor"
    TWO_FACTOR = "two_factor"


class StepUpMethod(StrEnum):
    """
    How a signed-in person confirms it is them before a sensitive action: a
    code of their authenticator app (or a recovery code) when they have one,
    otherwise a new login code sent to their phone or e-mail.
    """

    TOTP = "totp"
    LOGIN_CODE = "login_code"


class TotpFactorStatus(StrEnum):
    """
    An authenticator being set up (PENDING until its first code is entered)
    or in use (ACTIVE). A user has at most one.
    """

    PENDING = "pending"
    ACTIVE = "active"
