"""Where the owners hear about billing: their sign-in address, Telegram chats."""

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.users import UserDocument
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName


def telegram_contacts(business: BusinessDocument) -> list[ManagerContact]:
    """The business's Telegram chats linked to the platform bot."""

    return [
        contact
        for contact in business.manager_contacts
        if contact.channel is ManagerContactChannel.TELEGRAM
    ]


def owner_contact(
    owner: UserDocument, business: BusinessDocument
) -> ManagerContact | None:
    """An owner at their sign-in identity, in their cabinet language."""

    name = ManagerName(str(owner.display_name or business.name))
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
            channel=ManagerContactChannel.WHATSAPP,
            address=ManagerContactAddress(str(owner.phone_number)),
            language=owner.locale,
        )

    return None
