"""In-memory wiring of the knowledge slice for tests (no network, fixed clock)."""

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
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.knowledge.create_knowledge_item_use_case import (
    CreateKnowledgeItemUseCase,
)
from app.use_cases.knowledge.delete_knowledge_item_use_case import (
    DeleteKnowledgeItemUseCase,
)
from app.use_cases.knowledge.get_knowledge_item_use_case import (
    GetKnowledgeItemUseCase,
)
from app.use_cases.knowledge.get_price_use_case import GetPriceUseCase
from app.use_cases.knowledge.list_knowledge_items_use_case import (
    ListKnowledgeItemsUseCase,
)
from app.use_cases.knowledge.search_knowledge_use_case import SearchKnowledgeUseCase
from app.use_cases.knowledge.send_link_use_case import SendLinkUseCase
from app.use_cases.knowledge.update_knowledge_item_use_case import (
    UpdateKnowledgeItemUseCase,
)
from app.use_cases.knowledge.upsert_knowledge_items_use_case import (
    UpsertKnowledgeItemsUseCase,
)
from app.use_cases.profiles.compute_profile_gaps_use_case import (
    ComputeProfileGapsUseCase,
)
from app.use_cases.profiles.get_business_profile_use_case import (
    GetBusinessProfileUseCase,
)
from app.use_cases.profiles.get_niche_template_use_case import (
    GetNicheTemplateUseCase,
)
from app.use_cases.profiles.get_profile_wizard_use_case import (
    GetProfileWizardUseCase,
)
from app.use_cases.profiles.list_niche_templates_use_case import (
    ListNicheTemplatesUseCase,
)
from app.use_cases.profiles.save_profile_step_use_case import SaveProfileStepUseCase
from app.use_cases.profiles.save_profile_use_case import SaveProfileUseCase
from app.use_cases.resources.create_resource_use_case import CreateResourceUseCase
from app.use_cases.resources.create_schedule_exception_use_case import (
    CreateScheduleExceptionUseCase,
)
from app.use_cases.resources.delete_schedule_exception_use_case import (
    DeleteScheduleExceptionUseCase,
)
from app.use_cases.resources.list_resources_use_case import ListResourcesUseCase
from app.use_cases.resources.list_schedule_exceptions_use_case import (
    ListScheduleExceptionsUseCase,
)
from app.use_cases.resources.update_resource_use_case import UpdateResourceUseCase
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


class KnowledgeHarness:
    """Repositories, registry, fakes and every use case of the slice."""

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

        self.authorize_business_access = AuthorizeBusinessAccessUseCase(
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=self.wall_clock,
        )
        self.list_niche_templates = ListNicheTemplatesUseCase(
            niche_template_registry=self.niche_template_registry,
            localized_text_resolver=self.resolver,
        )
        self.get_niche_template = GetNicheTemplateUseCase(
            niche_template_registry=self.niche_template_registry,
            localized_text_resolver=self.resolver,
        )
        self.get_profile_wizard = GetProfileWizardUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.business_profile_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            resource_repo=self.resource_repo,
            niche_template_registry=self.niche_template_registry,
            localized_text_resolver=self.resolver,
        )
        self.get_business_profile = GetBusinessProfileUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.business_profile_repo,
        )
        self.save_profile_step = SaveProfileStepUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.business_profile_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            audit_log_repo=self.audit_log_repo,
            niche_template_registry=self.niche_template_registry,
            phone_number_parser=self.phone_number_parser,
            wall_clock=self.wall_clock,
        )
        self.save_profile = SaveProfileUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.business_profile_repo,
            audit_log_repo=self.audit_log_repo,
            niche_template_registry=self.niche_template_registry,
            phone_number_parser=self.phone_number_parser,
            wall_clock=self.wall_clock,
        )
        self.compute_profile_gaps = ComputeProfileGapsUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.business_profile_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            resource_repo=self.resource_repo,
            unanswered_question_repo=self.unanswered_question_repo,
            niche_template_registry=self.niche_template_registry,
            localized_text_resolver=self.resolver,
        )
        self.create_knowledge_item = CreateKnowledgeItemUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            niche_template_registry=self.niche_template_registry,
            wall_clock=self.wall_clock,
        )
        self.update_knowledge_item = UpdateKnowledgeItemUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            niche_template_registry=self.niche_template_registry,
            wall_clock=self.wall_clock,
        )
        self.delete_knowledge_item = DeleteKnowledgeItemUseCase(
            knowledge_item_repo=self.knowledge_item_repo,
        )
        self.get_knowledge_item = GetKnowledgeItemUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
        )
        self.list_knowledge_items = ListKnowledgeItemsUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
        )
        self.upsert_knowledge_items = UpsertKnowledgeItemsUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            niche_template_registry=self.niche_template_registry,
            wall_clock=self.wall_clock,
        )
        self.search_knowledge = SearchKnowledgeUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
        )
        self.get_price = GetPriceUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
        )
        self.send_link = SendLinkUseCase(
            business_profile_repo=self.business_profile_repo,
        )
        self.create_resource = CreateResourceUseCase(
            business_repo=self.business_repo,
            resource_repo=self.resource_repo,
            niche_template_registry=self.niche_template_registry,
            wall_clock=self.wall_clock,
        )
        self.update_resource = UpdateResourceUseCase(
            resource_repo=self.resource_repo,
            wall_clock=self.wall_clock,
        )
        self.list_resources = ListResourcesUseCase(resource_repo=self.resource_repo)
        self.create_schedule_exception = CreateScheduleExceptionUseCase(
            business_repo=self.business_repo,
            resource_repo=self.resource_repo,
            schedule_exception_repo=self.schedule_exception_repo,
            wall_clock=self.wall_clock,
        )
        self.list_schedule_exceptions = ListScheduleExceptionsUseCase(
            schedule_exception_repo=self.schedule_exception_repo,
        )
        self.delete_schedule_exception = DeleteScheduleExceptionUseCase(
            schedule_exception_repo=self.schedule_exception_repo,
        )

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
