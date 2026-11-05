"""A live restaurant with an owner, staff and a week of activity for value tests."""

from datetime import datetime

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus, LeadType
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.push_subscriptions import (
    PushSubscriptionDocument,
    PushSubscriptionKeys,
)
from app.schemas.domain.users import UserDocument
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    BookingValueMinor,
    PartySize,
)
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.notifications.constrained_strings import (
    PushAuthSecret,
    PushEndpointUrl,
    PushPublicKey,
)
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.notifications.staff_delivery_keys import push_subscription_id
from tests.notifications.test_web_push_encryption import AUTH_SECRET, RECEIVER_PUBLIC
from tests.operations.fakes import to_microseconds
from tests.value.value_world import ValueWorld

OWNER_EMAIL: str = "owner@example.com"
# 2026-09-01 in Tbilisi: the business existed before every period tested.
OPENED: datetime = datetime.fromisoformat("2026-08-01T10:00:00+04:00")


def at(local: str) -> Microseconds:
    return to_microseconds(datetime.fromisoformat(local))


class ValueScene:
    """One restaurant (Tbilisi, GEL), open 12:00 to 23:00 every day."""

    def __init__(
        self,
        world: ValueWorld | None = None,
        niche_key: NicheKey = NicheKey.RESTAURANT,
        currency_code: str = "GEL",
        country_code: str = "GE",
        owner_email: str | None = OWNER_EMAIL,
    ) -> None:
        self.world = world or ValueWorld()
        self.owner = self.add_user(owner_email, "ru")
        self.staff_id = UserId()
        business = self.world.add_business(
            niche_key=niche_key,
            currency_code=currency_code,
            country_code=country_code,
            owner_id=self.owner.id,
            staff_ids=(self.staff_id,),
        )
        business.status = BusinessStatus.LIVE
        business.created_at = at(OPENED.isoformat())
        self.world.business_repo.save(business)
        self.business: BusinessDocument = business
        self.world.add_profile(business)
        self.table = self.world.add_resource(business, "Table 4")
        self.contact = self.world.add_contact(business, "Nino")

    def add_user(self, email: str | None, locale: str) -> UserDocument:
        user = UserDocument(
            login_method=LoginMethod.EMAIL if email else LoginMethod.PHONE,
            email=None if email is None else EmailAddress(email),
            locale=LanguageTag(locale),
            is_verified=True,
        )
        self.world.user_repo.save(user)
        return user

    def conversation(
        self,
        local: str,
        channel: ChannelKind = ChannelKind.WHATSAPP,
        is_sandbox: bool = False,
        is_after_hours: bool = False,
    ) -> ConversationDocument:
        return self.world.add_conversation(
            self.business,
            self.contact,
            channel,
            is_sandbox=is_sandbox,
            is_after_hours=is_after_hours,
            created_at=datetime.fromisoformat(local),
        )

    def message(
        self,
        conversation: ConversationDocument,
        local: str,
        author: MessageAuthor = MessageAuthor.ASSISTANT,
    ) -> None:
        moment = at(local)
        self.world.message_repo.save(
            MessageDocument(
                conversation_id=conversation.id,
                business_id=self.business.id,
                direction=(
                    MessageDirection.INBOUND
                    if author is MessageAuthor.CUSTOMER
                    else MessageDirection.OUTBOUND
                ),
                author=author,
                text=MessageText("Hello"),
                created_at=moment,
                updated_at=moment,
            )
        )

    def booking(
        self,
        local: str,
        conversation: ConversationDocument | None,
        status: BookingStatus = BookingStatus.CONFIRMED,
        starts: str = "2026-10-10T19:00:00+04:00",
        is_sandbox: bool = False,
        value: tuple[int, str] | None = None,
    ) -> None:
        """`value`: what the booking is worth, in minor units of a currency."""

        moment = at(local)
        start_seconds = int(at(starts)) // 1_000_000
        self.world.booking_repo.save(
            BookingDocument(
                business_id=self.business.id,
                resource_id=self.table.id,
                contact_id=self.contact.id,
                conversation_id=None if conversation is None else conversation.id,
                starts_at=BookingStartsAtUnixSeconds(start_seconds),
                ends_at=BookingEndsAtUnixSeconds(start_seconds + 7_200),
                party_size=PartySize(2),
                status=status,
                source_channel=ChannelKind.WHATSAPP,
                is_sandbox=is_sandbox,
                value_minor=None if value is None else BookingValueMinor(value[0]),
                currency_code=None if value is None else CurrencyCode(value[1]),
                created_at=moment,
                updated_at=moment,
            )
        )

    def lead(self, local: str) -> None:
        moment = at(local)
        self.world.lead_repo.save(
            LeadDocument(
                business_id=self.business.id,
                contact_id=self.contact.id,
                lead_type=LeadType.BANQUET,
                details=LeadDetails("Birthday for 20"),
                source_channel=ChannelKind.WHATSAPP,
                created_at=moment,
                updated_at=moment,
            )
        )

    def handoff(self, conversation: ConversationDocument, local: str) -> None:
        moment = at(local)
        self.world.handoff_repo.save(
            HandoffDocument(
                business_id=self.business.id,
                conversation_id=conversation.id,
                contact_id=self.contact.id,
                reason=HandoffReason.COMPLAINT,
                summary=HandoffSummary("Cold soup"),
                urgency=HandoffUrgency.NORMAL,
                created_at=moment,
                updated_at=moment,
            )
        )

    def device(self, user: UserDocument, language: str) -> PushSubscriptionDocument:
        endpoint = f"https://push.example.com/{user.id}-{language}"
        device = PushSubscriptionDocument(
            id=push_subscription_id(self.business.id, user.id, endpoint),
            business_id=self.business.id,
            user_id=user.id,
            endpoint=PushEndpointUrl(endpoint),
            keys=PushSubscriptionKeys(
                p256dh=PushPublicKey(RECEIVER_PUBLIC), auth=PushAuthSecret(AUTH_SECRET)
            ),
            language=LanguageTag(language),
        )
        self.world.push_subscription_repo.save(device)
        return device
