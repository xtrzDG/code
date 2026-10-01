from enum import StrEnum


class LoginMethod(StrEnum):
    """Identifier an owner uses to sign in."""

    PHONE = "phone"
    EMAIL = "email"
