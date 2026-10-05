"""
Who sees customers' phone numbers in Customers and the search: owners
always; staff only when the owner allowed it (Customers → settings);
platform support looking in never (minimal access). Everyone else sees a
masked phone ("+995 ••• ••• •34") that is still enough to recognise a
caller.
"""

from app.contracts.repositories.customer_repositories import (
    CustomerSettingsRepoContract,
)
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.customer_settings import CustomerSettingsDocument
from app.schemas.dto.contacts import ContactSummaryView
from app.schemas.typings.contacts.booleans import StaffSeesCustomerPhones
from app.schemas.typings.contacts.strings import MaskedPhoneNumber
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.prefixed_id import UserId

MASK: str = "•"
# Digits kept at the start (after "+") and at the end of a masked phone.
SHOWN_LEADING_DIGITS: int = 3
SHOWN_TRAILING_DIGITS: int = 2


def member_role(
    business: BusinessDocument, user_id: UserId
) -> BusinessMemberRole | None:
    """The person's role in the business; None for platform support."""

    for member in business.members:
        if member.user_id == user_id:
            return member.role

    return None


def sees_phone_numbers(
    business: BusinessDocument,
    user_id: UserId,
    settings_repo: CustomerSettingsRepoContract,
) -> StaffSeesCustomerPhones:
    role: BusinessMemberRole | None = member_role(business, user_id)
    if role is BusinessMemberRole.OWNER:
        return True

    if role is None:
        return False

    settings: CustomerSettingsDocument | None = settings_repo.get_by_business(
        business.id
    )
    return settings is not None and settings.staff_sees_phone_numbers


def mask_phone_number(phone_number: E164PhoneNumber) -> MaskedPhoneNumber:
    """'+995599123456' -> '+995 ••• ••• •56': the country prefix and the last digits."""

    digits: str = str(phone_number).removeprefix("+")
    hidden: int = max(len(digits) - SHOWN_LEADING_DIGITS - SHOWN_TRAILING_DIGITS, 0)
    masked: str = MASK * hidden + digits[len(digits) - SHOWN_TRAILING_DIGITS :]
    groups: list[str] = [
        masked[index : index + 3] for index in range(0, len(masked), 3)
    ]
    return MaskedPhoneNumber(f"+{digits[:SHOWN_LEADING_DIGITS]} {' '.join(groups)}")


def protect_phone(view: ContactSummaryView, sees_phones: bool) -> ContactSummaryView:
    """The row as this viewer may see it: the phone masked unless allowed."""

    if sees_phones or view.phone_number is None:
        return view

    return view.model_copy(
        update={
            "phone_number": None,
            "masked_phone_number": mask_phone_number(view.phone_number),
            "is_phone_masked": True,
        }
    )
