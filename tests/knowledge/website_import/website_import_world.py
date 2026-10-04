"""
The website import wired for tests: real use cases, fetcher, sanitizer and
reader adapter; a fake website, the scripted model, in-memory storage.
"""

import json
import re
from collections.abc import Callable

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.adapters.llm.website_extraction.website_extraction_adapter import (
    WebsiteExtractionAdapter,
)
from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.clients.http.safe_http_fetcher import SafeHttpFetcher
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.repositories.billing_repositories import UsageEventRepository
from app.repositories.website_import_repository import WebsiteImportRepository
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.website_imports import WebsiteImportDocument
from app.schemas.dto.conversations import LlmRequest, LlmResponse
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.dto.website_import import (
    CurrentWebsiteImport,
    GetWebsiteImportQuery,
    StartWebsiteImportCommand,
    WebsiteImportView,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.booleans import IsFinalJobAttempt
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.knowledge.website_import.get_website_import_use_case import (
    GetWebsiteImportUseCase,
)
from app.use_cases.knowledge.website_import.run_website_import_use_case import (
    RunWebsiteImportUseCase,
)
from app.use_cases.knowledge.website_import.start_website_import_use_case import (
    StartWebsiteImportUseCase,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.foundation.access_support import ACCESS_SETTINGS
from tests.knowledge.knowledge_store import KnowledgeStore
from tests.knowledge.website_import.fake_website import FakeWebsite
from tests.knowledge.website_import.recording_job_queue import (
    QueuedJob,
    RecordingJobQueue,
)
from tests.knowledge.website_import.site_fixtures import (
    PUBLIC_ADDRESS,
    reader_answer,
    site_pages,
)
from tests.live_events.recording_event_publisher import RecordingEventPublisher

PAGE_ADDRESS: re.Pattern[str] = re.compile(r"Page address: (\S+)")


class TokenCountingLlm(ScriptedLlmAdapter):
    """The scripted reader, reporting 1,000 input and 200 output tokens a call."""

    def complete(self, request: LlmRequest) -> LlmResponse:
        return (
            super()
            .complete(request)
            .model_copy(
                update={
                    "input_tokens": LlmTokenCount(1000),
                    "output_tokens": LlmTokenCount(200),
                }
            )
        )


def answer_by_page(request: LlmRequest) -> ScriptedLlmTurn:
    """The scripted reader: the fixture answer of the page it is shown."""

    turn: object = json.loads(str(request.transcript[0]))
    text: str = str(turn["content"][0]["text"])  # type: ignore[index]
    match: re.Match[str] | None = PAGE_ADDRESS.search(text)
    assert match is not None
    return ScriptedLlmTurn(text=MessageText(reader_answer(match.group(1))))


class WebsiteImportWorld(KnowledgeStore):
    """A Tbilisi restaurant whose owner imports https://cafe.example."""

    def __init__(self) -> None:
        super().__init__()
        self.owner_id: UserId = UserId()
        self.staff_id: UserId = UserId()
        self.business: BusinessDocument = self.add_business(
            owner_id=self.owner_id, staff_ids=(self.staff_id,)
        )
        self.website = FakeWebsite({"cafe.example": [PUBLIC_ADDRESS]}, site_pages())
        self.fetcher = SafeHttpFetcher(
            resolver=self.website.resolve, connector=self.website.connect
        )
        # Tests swap the reader's answers by replacing `respond`.
        self.respond: Callable[[LlmRequest], ScriptedLlmTurn] = answer_by_page
        self.llm = TokenCountingLlm(lambda request: self.respond(request))
        self.website_import_repo = WebsiteImportRepository(
            InMemoryDocumentCollectionAdapter[WebsiteImportDocument](
                WebsiteImportDocument
            )
        )
        self.usage_event_repo = UsageEventRepository(
            InMemoryDocumentCollectionAdapter[UsageEventDocument](UsageEventDocument)
        )
        self.job_queue = RecordingJobQueue()
        self.events = RecordingEventPublisher()
        authorize = AuthorizeBusinessAccessUseCase(
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=self.wall_clock,
            session_assurance=SessionAssuranceContext(),
            app_settings=ACCESS_SETTINGS,
        )
        self.start = StartWebsiteImportUseCase(
            authorize_business_access=authorize,
            safe_http_fetcher=self.fetcher,
            website_import_repo=self.website_import_repo,
            rate_limit_registry=RequestRateLimitRegistry(
                InMemoryRateLimitBucketAdapter()
            ),
            job_queue=self.job_queue,
            live_events=self.events,
            wall_clock=self.wall_clock,
        )
        self.get = GetWebsiteImportUseCase(
            authorize_business_access=authorize,
            website_import_repo=self.website_import_repo,
            knowledge_item_repo=self.knowledge_item_repo,
        )
        self.reader = WebsiteExtractionAdapter(self.llm, LlmModelId("gpt-5-mini"))
        self.run_job = RunWebsiteImportUseCase(
            website_import_repo=self.website_import_repo,
            business_repo=self.business_repo,
            niche_template_registry=self.niche_template_registry,
            knowledge_item_repo=self.knowledge_item_repo,
            usage_event_repo=self.usage_event_repo,
            safe_http_fetcher=self.fetcher,
            website_extraction_adapter=self.reader,
            live_events=self.events,
            wall_clock=self.wall_clock,
        )

    def start_import(
        self, url: str = "https://cafe.example", user_id: UserId | None = None
    ) -> WebsiteImportView:
        return self.start.run(
            StartWebsiteImportCommand(
                user_id=self.owner_id if user_id is None else user_id,
                business_id=self.business.id,
                url=WebLink(url),
            )
        )

    def run_queued(self, is_final_attempt: bool = False) -> JobReport:
        """Run the last queued import job, as the worker would."""

        job: QueuedJob = self.job_queue.jobs[-1]
        return self.run_job.run(
            QueuedJobInput(
                job_id=job.job_id,
                job_name=job.name,
                payload=job.payload,
                business_id=job.business_id,
                is_final_attempt=IsFinalJobAttempt(is_final_attempt),
            )
        )

    def current(self) -> CurrentWebsiteImport:
        return self.get.run(
            GetWebsiteImportQuery(user_id=self.owner_id, business_id=self.business.id)
        )
