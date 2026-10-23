"""In-memory wiring of the knowledge slice for tests (no network, fixed clock)."""

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.registries.niches.niche_value_registry import NicheValueRegistry
from app.repositories.billing_repositories import UsageEventRepository
from app.schemas.domain.billing import UsageEventDocument
from app.use_cases.knowledge.aliases.suggest_knowledge_aliases_use_case import (
    SuggestKnowledgeAliasesUseCase,
)
from app.use_cases.knowledge.create_knowledge_item_use_case import (
    CreateKnowledgeItemUseCase,
)
from app.use_cases.knowledge.delete_knowledge_item_use_case import (
    DeleteKnowledgeItemUseCase,
)
from app.use_cases.knowledge.get_knowledge_item_use_case import GetKnowledgeItemUseCase
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
from app.use_cases.profiles.get_niche_template_use_case import GetNicheTemplateUseCase
from app.use_cases.profiles.get_profile_wizard_use_case import GetProfileWizardUseCase
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
from app.use_cases.spend_guard.admit_owner_action_use_case import (
    AdmitOwnerActionUseCase,
)
from app.utilities.conversations.language_detector import LanguageDetector
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.data_tasks.data_task_support import data_task_states, no_data_tasks
from tests.foundation.access_support import ACCESS_SETTINGS
from tests.foundation.brand_repositories import in_memory_brand_knowledge_repo
from tests.foundation.support_access_builders import build_authorize_business_access
from tests.knowledge.cross_language.fakes import PhraseBookAliasSuggester
from tests.knowledge.knowledge_store import KnowledgeStore
from tests.knowledge.website_import.recording_job_queue import RecordingJobQueue


class KnowledgeHarness(KnowledgeStore):
    """Repositories, registry, fakes and every use case of the slice."""

    def __init__(self) -> None:
        super().__init__()
        self.authorize_business_access = build_authorize_business_access(
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=self.wall_clock,
            session_assurance=SessionAssuranceContext(),
            app_settings=ACCESS_SETTINGS,
        )
        self.brand_knowledge_repo = in_memory_brand_knowledge_repo()
        self.list_niche_templates = ListNicheTemplatesUseCase(
            niche_template_registry=self.niche_template_registry,
            localized_text_resolver=self.resolver,
            niche_value_registry=NicheValueRegistry(),
        )
        self.get_niche_template = GetNicheTemplateUseCase(
            niche_template_registry=self.niche_template_registry,
            localized_text_resolver=self.resolver,
        )
        self.get_profile_wizard = GetProfileWizardUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.business_profile_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            brand_knowledge_item_repo=self.brand_knowledge_repo,
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
            brand_knowledge_item_repo=self.brand_knowledge_repo,
            resource_repo=self.resource_repo,
            unanswered_question_repo=self.unanswered_question_repo,
            niche_template_registry=self.niche_template_registry,
            localized_text_resolver=self.resolver,
        )
        self.job_queue = RecordingJobQueue()
        self.create_knowledge_item = CreateKnowledgeItemUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            resource_repo=self.resource_repo,
            niche_template_registry=self.niche_template_registry,
            wall_clock=self.wall_clock,
            job_queue=self.job_queue,
        )
        self.update_knowledge_item = UpdateKnowledgeItemUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            resource_repo=self.resource_repo,
            niche_template_registry=self.niche_template_registry,
            wall_clock=self.wall_clock,
            job_queue=self.job_queue,
        )
        self.delete_knowledge_item = DeleteKnowledgeItemUseCase(
            knowledge_item_repo=self.knowledge_item_repo,
            job_queue=self.job_queue,
        )
        self.get_knowledge_item = GetKnowledgeItemUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            resource_repo=self.resource_repo,
        )
        self.data_task_states = data_task_states()
        self.list_knowledge_items = ListKnowledgeItemsUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            resource_repo=self.resource_repo,
            data_task_registry=no_data_tasks(),
            data_task_state_repo=self.data_task_states,
        )
        self.upsert_knowledge_items = UpsertKnowledgeItemsUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            resource_repo=self.resource_repo,
            niche_template_registry=self.niche_template_registry,
            wall_clock=self.wall_clock,
        )
        self.alias_suggester = PhraseBookAliasSuggester()
        self.usage_event_repo = UsageEventRepository(
            InMemoryDocumentCollectionAdapter[UsageEventDocument](UsageEventDocument)
        )
        self.suggest_knowledge_aliases = SuggestKnowledgeAliasesUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            resource_repo=self.resource_repo,
            usage_event_repo=self.usage_event_repo,
            alias_suggester=self.alias_suggester,
            language_detector=LanguageDetector(),
            admit_owner_action=AdmitOwnerActionUseCase(
                RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter()),
                self.wall_clock,
            ),
            wall_clock=self.wall_clock,
        )
        self.search_knowledge = SearchKnowledgeUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            brand_knowledge_item_repo=self.brand_knowledge_repo,
        )
        self.get_price = GetPriceUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            brand_knowledge_item_repo=self.brand_knowledge_repo,
        )
        self.send_link = SendLinkUseCase(
            business_profile_repo=self.business_profile_repo,
        )
        self.create_resource = CreateResourceUseCase(
            business_repo=self.business_repo,
            resource_repo=self.resource_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            niche_template_registry=self.niche_template_registry,
            wall_clock=self.wall_clock,
        )
        self.update_resource = UpdateResourceUseCase(
            resource_repo=self.resource_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            wall_clock=self.wall_clock,
        )
        self.list_resources = ListResourcesUseCase(
            resource_repo=self.resource_repo,
            knowledge_item_repo=self.knowledge_item_repo,
        )
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
