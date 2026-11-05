"""Where invoices and receipts are e-mailed for a business."""

from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing_profiles import BillingProfileDocument
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.users import UserDocument
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName


def find_billing_contacts(
    business: BusinessDocument,
    profile: BillingProfileDocument | None,
    user_repo: UserRepoContract,
) -> list[ManagerContact]:
    """
    The billing e-mail of the saved billing details; without one, every
    owner who signs in with an e-mail address (an owner who signs in by
    phone downloads the PDFs in the cabinet). In the owner language.
    """

    if profile is not None and profile.billing_email is not None:
        return [
            ManagerContact(
                name=ManagerName(str(profile.legal_name)),
                channel=ManagerContactChannel.EMAIL,
                address=ManagerContactAddress(str(profile.billing_email)),
                language=business.owner_language,
            )
        ]

    contacts: list[ManagerContact] = []
    for member in business.members:
        if member.role is not BusinessMemberRole.OWNER:
            continue

        owner: UserDocument | None = user_repo.get(member.user_id)
        if owner is None or owner.email is None:
            continue

        contacts.append(
            ManagerContact(
                name=ManagerName(str(owner.display_name or business.name)),
                channel=ManagerContactChannel.EMAIL,
                address=ManagerContactAddress(str(owner.email)),
                language=business.owner_language,
            )
        )

    return contacts
