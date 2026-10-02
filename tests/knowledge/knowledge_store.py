"""The knowledge harness's storage: a settable clock, repositories and fakes."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.repositories.booking_repositories import UnansweredQuestionRepository
from app.repositories.business_repositories import (
    BusinessProfileRepository,
    BusinessRepository,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.knowledge_repositories import (
    KnowledgeItemRepository,
    ResourceRepository,
    ScheduleExceptionRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import (
    BusinessDocument,
    BusinessMember,
    ManagerContact,
)
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.users.prefixed_id import UserId
from tests.knowledge.fakes import FakeLocalizedTextResolver, FakePhoneNumberParser

# 2026-10-01 09:00:00 UTC: 13:00 in Tbilisi, 05:00 in New York, 18:00 in Tokyo.
DEFAULT_NOW: datetime = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


def to_nanoseconds(moment: datetime) -> int:
    return int(moment.timestamp()) * 1_000_000_000


@dataclass
class MutableClockSource:
    """Nanoseconds the wall clock reports; tests move it explicitly."""

    nanoseconds: int = field(default_factory=lambda: to_nanoseconds(DEFAULT_NOW))

    def set(self, moment: datetime) -> None:
        self.nanoseconds = to_nanoseconds(moment)

    def read(self) -> int:
        return self.nanoseconds


class KnowledgeStore:
    """Clock, repositories, the niche registry and fakes of the knowledge slice."""

    def __init__(self) -> None:
        self.clock_source: MutableClockSource = MutableClockSource()
        self.wall_clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=self.clock_source.read,
        )
        self.business_repo: BusinessRepository = BusinessRepository(
            InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
        )
        self.user_repo: UserRepository = UserRepository(
            InMemoryDocumentCollectionAdapter[UserDocument](UserDocument)
        )
        self.business_profile_repo: BusinessProfileRepository = (
            BusinessProfileRepository(
                InMemoryDocumentCollectionAdapter[BusinessProfileDocument](
                    BusinessProfileDocument
                )
            )
        )
        self.knowledge_item_repo: KnowledgeItemRepository = KnowledgeItemRepository(
            InMemoryDocumentCollectionAdapter[KnowledgeItemDocument](
                KnowledgeItemDocument
            )
        )
        self.resource_repo: ResourceRepository = ResourceRepository(
            InMemoryDocumentCollectionAdapter[ResourceDocument](ResourceDocument)
        )
        self.schedule_exception_repo: ScheduleExceptionRepository = (
            ScheduleExceptionRepository(
                InMemoryDocumentCollectionAdapter[ScheduleExceptionDocument](
                    ScheduleExceptionDocument
                )
            )
        )
        self.unanswered_question_repo: UnansweredQuestionRepository = (
            UnansweredQuestionRepository(
                InMemoryDocumentCollectionAdapter[UnansweredQuestionDocument](
                    UnansweredQuestionDocument
                )
            )
        )
        self.audit_log_repo: AuditLogRepository = AuditLogRepository(
            InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](
                AuditLogEntryDocument
            )
        )
        self.niche_template_registry: NicheTemplateRegistry = NicheTemplateRegistry()
        self.resolver: FakeLocalizedTextResolver = FakeLocalizedTextResolver()
        self.phone_number_parser: FakePhoneNumberParser = FakePhoneNumberParser()

    def add_business(
        self,
        niche_key: NicheKey = NicheKey.RESTAURANT,
        country_code: str = "GE",
        currency_code: str = "GEL",
        timezone: str = "Asia/Tbilisi",
        languages: tuple[str, ...] = ("ka", "ru", "en"),
        owner_language: str = "ka",
        owner_id: UserId | None = None,
        staff_ids: tuple[UserId, ...] = (),
        has_manager_contact: bool = False,
    ) -> BusinessDocument:
        """Store a business of any country; defaults describe a Tbilisi venue."""

        members: list[BusinessMember] = [
            BusinessMember(
                user_id=owner_id if owner_id is not None else UserId(),
                role=BusinessMemberRole.OWNER,
            )
        ]
        members.extend(
            BusinessMember(user_id=staff_id, role=BusinessMemberRole.STAFF)
            for staff_id in staff_ids
        )
        manager_contacts: list[ManagerContact] = []
        if has_manager_contact:
            manager_contacts.append(
                ManagerContact(
                    name=ManagerName("Nino"),
                    channel=ManagerContactChannel.TELEGRAM,
                    address=ManagerContactAddress("@nino_manager"),
                    language=LanguageTag(owner_language),
                )
            )

        business = BusinessDocument(
            name=BusinessName("Test venue"),
            niche_key=niche_key,
            country_code=CountryCode(country_code),
            timezone=TimezoneName(timezone),
            currency_code=CurrencyCode(currency_code),
            languages=[LanguageTag(language) for language in languages],
            default_language=LanguageTag(languages[0]),
            owner_language=LanguageTag(owner_language),
            plan_key=PlanKey.VOICE_AND_CHAT,
            data_region=DataRegion.EU,
            members=members,
            manager_contacts=manager_contacts,
        )
        self.business_repo.save(business)
        return business
