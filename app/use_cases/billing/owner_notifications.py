"""Billing messages to the owners of a business."""

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.users import UserDocument
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName


def notify_business_owners(
    business: BusinessDocument,
    user_repo: UserRepoContract,
    notifier: ManagerNotificationFacilitatorContract,
    text: MessageText,
) -> int:
    """
    Send `text` to every owner; return how many deliveries succeeded.

    Owners are reached at their sign-in identity: e-mail when they have one,
    otherwise their phone number on WhatsApp. Delivery failures never raise.
    """

    delivered: int = 0
    for member in business.members:
        if member.role is not BusinessMemberRole.OWNER:
            continue

        owner: UserDocument | None = user_repo.get(member.user_id)
        if owner is None:
            continue

        contact: ManagerContact | None = build_owner_contact(owner, business)
        if contact is not None and notifier.notify(contact, text):
            delivered += 1

    return delivered


def build_owner_contact(
    owner: UserDocument,
    business: BusinessDocument,
) -> ManagerContact | None:
    """Where an owner receives billing messages, in the owner language."""

    name = ManagerName(str(owner.display_name or business.name))
    if owner.email is not None:
        return ManagerContact(
            name=name,
            channel=ManagerContactChannel.EMAIL,
            address=ManagerContactAddress(str(owner.email)),
            language=business.owner_language,
        )

    if owner.phone_number is not None:
        return ManagerContact(
            name=name,
            channel=ManagerContactChannel.WHATSAPP,
            address=ManagerContactAddress(str(owner.phone_number)),
            language=business.owner_language,
        )

    return None
