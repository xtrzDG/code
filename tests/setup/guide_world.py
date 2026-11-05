"""
A business with its owner, contacts and devices over in-memory storage,
for the guide after the launch, the milestone announcements and the
activation nudges (the staff alert facilitator and the nudge facilitator
are the real ones, their outbox and devices recorded).
"""

from datetime import datetime, timedelta

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.setup.owner_nudge_facilitator import OwnerNudgeFacilitator
from app.repositories.activation_repositories import NudgeSentRepository
from app.repositories.business_repositories import (
    BusinessRepository,
    ChannelRepository,
)
from app.repositories.setup_repositories import (
    ActivationEventRepository,
    SetupStateRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.setup import (
    ActivationEventDocument,
    NudgeSentDocument,
    SetupStateDocument,
)
from app.schemas.domain.users import UserDocument
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from tests.notifications.alert_world import AlertWorld, build_business
from tests.operations.fakes import FakeLocalizedTextResolver

# Thursday 2026-10-01 11:00 in Tbilisi: daytime, when nudges go out.
MORNING: datetime = datetime.fromisoformat("2026-10-01T11:00:00+04:00")


def business_with_contacts(contacts: list[ManagerContact]) -> BusinessDocument:
    business = build_business(UserId(), UserId())
    return business.model_copy(update={"manager_contacts": contacts})


class GuideWorld(AlertWorld):
    """The alert world, plus the stores and the nudges of the activation job."""

    def __init__(self) -> None:
        super().__init__()
        self.moment: datetime = MORNING
        self.clock.move_to(MORNING)
        self.business = self.business.model_copy(
            update={"created_at": self.now(), "updated_at": self.now()}
        )
        self.businesses = BusinessRepository(
            InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
        )
        self.businesses.save(self.business)
        self.users = UserRepository(
            InMemoryDocumentCollectionAdapter[UserDocument](UserDocument)
        )
        self.users.save(
            UserDocument(
                id=self.owner,
                login_method=LoginMethod.EMAIL,
                email=EmailAddress("owner@example.com"),
                locale=LanguageTag("ru"),
            )
        )
        self.channels = ChannelRepository(
            InMemoryDocumentCollectionAdapter[ChannelDocument](ChannelDocument)
        )
        self.events = ActivationEventRepository(
            InMemoryDocumentCollectionAdapter[ActivationEventDocument](
                ActivationEventDocument
            )
        )
        self.states = SetupStateRepository(
            InMemoryDocumentCollectionAdapter[SetupStateDocument](SetupStateDocument)
        )
        self.nudges_sent = NudgeSentRepository(
            InMemoryDocumentCollectionAdapter[NudgeSentDocument](NudgeSentDocument)
        )
        self.nudges = OwnerNudgeFacilitator(
            user_repo=self.users,
            push_subscription_repo=self.subscriptions,
            notification_preferences_repo=self.preferences,
            manager_notifier=self.notifier,
            push_queue=self.push_queue,
            link_signer=StaffLinkSigner(None),
            localized_text_resolver=FakeLocalizedTextResolver(),
            app_settings=self.settings,
            wall_clock=self.clock.wall_clock,
        )

    def now(self) -> Microseconds:
        return self.clock.wall_clock.now_unix()

    def advance(self, days: float = 0, hours: float = 0) -> None:
        self.moment += timedelta(days=days, hours=hours)
        self.clock.move_to(self.moment)

    def connect(self, kind: ChannelKind) -> None:
        self.channels.save(
            ChannelDocument(
                business_id=self.business.id,
                kind=kind,
                status=ChannelStatus.CONNECTED,
            )
        )
