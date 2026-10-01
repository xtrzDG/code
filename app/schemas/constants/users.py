from enum import StrEnum


class LoginMethod(StrEnum):
    """Identifier a user signs in with."""

    PHONE = "phone"
    EMAIL = "email"


class BusinessMemberRole(StrEnum):
    """Role of a user inside one business."""

    OWNER = "owner"
    STAFF = "staff"
