"""
Where the platform reaches a business's owners for what the DPA says it
must tell the Client (a breach, a change of sub-processors): each owner's
sign-in e-mail, else the sign-in phone by SMS, in the owner's cabinet
language. Staff are not told: the Client is the owner.
"""

from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.users import UserDocument
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName


def owner_contacts(
    business: BusinessDocument, user_repo: UserRepoContract
) -> list[ManagerContact]:
    """One contact per owner who has a sign-in address, in member order."""

    contacts: list[ManagerContact] = []
    for member in business.members:
        if member.role is not BusinessMemberRole.OWNER:
            continue

        owner: UserDocument | None = user_repo.get(member.user_id)
        contact: ManagerContact | None = None if owner is None else contact_of(owner)
        if contact is not None:
            contacts.append(contact)

    return contacts


def contact_of(owner: UserDocument) -> ManagerContact | None:
    """The owner's sign-in e-mail, else the sign-in phone by SMS."""

    name = ManagerName(str(owner.display_name or owner.email or owner.phone_number))
    if owner.email is not None:
        return ManagerContact(
            name=name,
            channel=ManagerContactChannel.EMAIL,
            address=ManagerContactAddress(str(owner.email)),
            language=owner.locale,
        )

    if owner.phone_number is not None:
        return ManagerContact(
            name=name,
            channel=ManagerContactChannel.SMS,
            address=ManagerContactAddress(str(owner.phone_number)),
            language=owner.locale,
        )

    return None
