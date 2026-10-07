"""Which partner a signed-in person is: the one with their phone or e-mail."""

from app.contracts.repositories.referral_repositories import PartnerRepoContract
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.users import UserDocument


def is_partner_person(partner: PartnerDocument, user: UserDocument) -> bool:
    """Whether the user signs in with the partner's phone number or e-mail."""

    same_phone: bool = (
        partner.phone_number is not None and user.phone_number == partner.phone_number
    )
    same_email: bool = partner.email is not None and user.email == partner.email
    return same_phone or same_email


def find_partner_of(
    partner_repo: PartnerRepoContract, user: UserDocument
) -> PartnerDocument | None:
    """The partner the user is (by their verified phone number or e-mail)."""

    if not user.is_verified:
        return None

    if user.phone_number is not None:
        by_phone: PartnerDocument | None = partner_repo.find_by_phone_number(
            user.phone_number
        )
        if by_phone is not None:
            return by_phone

    if user.email is not None:
        return partner_repo.find_by_email(user.email)

    return None
