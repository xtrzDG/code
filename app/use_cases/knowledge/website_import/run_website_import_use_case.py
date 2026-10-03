from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.billing_repositories import UsageEventRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.repositories.website_import_repositories import (
    WebsiteImportRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.web_fetching import SafeHttpFetcherContract
from app.contracts.website_import import WebsiteExtractionAdapterContract
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.website_import import (
    WebsiteImportProblem,
    WebsiteImportStatus,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.website_imports import WebsiteImportDocument
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.website_import import (
    SanitizedWebPage,
    WebsiteImportJobPayload,
    WebsitePageExtraction,
    WebsitePageExtractionRequest,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.menu_import.constrained_integers import MenuLineCount
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.constrained_strings import ErrorReasonDetail
from app.schemas.typings.web_fetching.constrained_strings import WebResourceUrl
from app.schemas.typings.website_import.constrained_integers import (
    WebsiteImportItemCount,
    WebsitePageCount,
)
from app.use_cases.knowledge.website_import.website_import_drafts import (
    WebsiteImportDrafts,
)
from app.use_cases.knowledge.website_import.website_import_problems import problem_of
from app.use_cases.knowledge.website_import.website_import_progress import (
    FINISHED_STATUSES,
    WebsiteImportProgress,
)
from app.use_cases.knowledge.website_import.website_import_usage import (
    record_reading_usage,
)
from app.use_cases.knowledge.website_import.website_page_fetching import (
    fetch_page,
    plan_pages,
)
from app.utilities.knowledge.knowledge_item_checks import ALWAYS_ALLOWED_KINDS

INTERRUPTED_DETAIL: ErrorReasonDetail = ErrorReasonDetail("worker_failed")
READER_FAILED_DETAIL: ErrorReasonDetail = ErrorReasonDetail("reader_failed")


@dataclass
class ReadingTally:
    """What reading the pages came to."""

    pages_read: int = 0
    reader_failures: int = 0


class RunWebsiteImportUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    The worker's job of one website import: read the start page, plan up
    to 14 more pages of the same site (sitemap.xml and the start page's
    links, most useful first), and let the reader model find the FAQ,
    policies and offer on each, one call per page. The facts become
    switched-off knowledge drafts of the import's batch (each fact once,
    with the page it came from); nothing is used by the assistant before
    the owner confirms it. Every model call is recorded as usage with its
    cost; each step is announced to the cabinet.

    A page that cannot be fetched or read is skipped. The import fails when
    its start page cannot be fetched, or when the reader model could read
    no page at all. A job of an import that was replaced or finished does
    nothing; a repeated run of an interrupted import starts it over; on the
    job's last attempt an unexpected error marks the import interrupted.
    """

    def __init__(
        self,
        website_import_repo: WebsiteImportRepoContract,
        business_repo: BusinessRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        usage_event_repo: UsageEventRepoContract,
        safe_http_fetcher: SafeHttpFetcherContract,
        website_extraction_adapter: WebsiteExtractionAdapterContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._website_import_repo: WebsiteImportRepoContract = website_import_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._safe_http_fetcher: SafeHttpFetcherContract = safe_http_fetcher
        self._website_extraction_adapter: WebsiteExtractionAdapterContract = (
            website_extraction_adapter
        )
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: QueuedJobInput) -> JobReport:
        payload = WebsiteImportJobPayload.model_validate_json(str(input_data.payload))
        if input_data.business_id is None:
            return JobReport()

        website_import: WebsiteImportDocument | None = (
            self._website_import_repo.get_by_business(input_data.business_id)
        )
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if (
            website_import is None
            or business is None
            or website_import.import_id != payload.import_id
            or website_import.status in FINISHED_STATUSES
        ):
            return JobReport()

        progress = WebsiteImportProgress(
            self._website_import_repo,
            self._live_events,
            self._wall_clock,
            business.id,
            website_import.import_id,
        )
        try:
            pages_read: int = self._read_site(business, website_import, progress)
        except Exception:
            if input_data.is_final_attempt:
                progress.finish(WebsiteImportProblem.INTERRUPTED, INTERRUPTED_DETAIL)
            raise

        return JobReport(processed_count=ProcessedItemCount(pages_read))

    def _read_site(
        self,
        business: BusinessDocument,
        website_import: WebsiteImportDocument,
        progress: WebsiteImportProgress,
    ) -> int:
        drafts = WebsiteImportDrafts(
            self._knowledge_item_repo, business, website_import.batch_id
        )
        if website_import.status is WebsiteImportStatus.READING:
            drafts.discard_earlier_attempt()
        progress.update(start_reading)

        try:
            start_page: SanitizedWebPage = fetch_page(
                self._safe_http_fetcher, WebResourceUrl(str(website_import.url))
            )
        except WebFetchError as error:
            progress.finish(problem_of(error), error.detail)
            return 0

        planned: list[WebResourceUrl] = plan_pages(
            self._safe_http_fetcher, start_page, str(website_import.url)
        )

        def plan(stored: WebsiteImportDocument) -> None:
            stored.pages_planned = WebsitePageCount(len(planned) + 1)

        progress.update(plan)
        tally = ReadingTally()
        self._read_page(business, start_page, drafts, progress, tally)
        for url in planned:
            try:
                page: SanitizedWebPage = fetch_page(self._safe_http_fetcher, url)
            except WebFetchError:
                progress.update(count_skipped_page)
                continue

            self._read_page(business, page, drafts, progress, tally)

        if tally.pages_read == 0 and tally.reader_failures > 0:
            progress.finish(
                WebsiteImportProblem.READER_UNAVAILABLE, READER_FAILED_DETAIL
            )
        else:
            progress.finish()

        return tally.pages_read

    def _read_page(
        self,
        business: BusinessDocument,
        page: SanitizedWebPage,
        drafts: WebsiteImportDrafts,
        progress: WebsiteImportProgress,
        tally: ReadingTally,
    ) -> None:
        if str(page.text).strip() == "":
            progress.update(count_skipped_page)
            return

        try:
            extraction: WebsitePageExtraction = (
                self._website_extraction_adapter.extract(
                    WebsitePageExtractionRequest(
                        page=page,
                        allowed_kinds=self._allowed_kinds(business),
                        language=business.default_language,
                        currency_code=business.currency_code,
                    )
                )
            )
        except ExternalServiceError:
            tally.reader_failures += 1
            progress.update(count_skipped_page)
            return

        now: Microseconds = progress.now()
        cost: CostMicroUsd = record_reading_usage(
            self._usage_event_repo, business.id, extraction, now
        )
        if not extraction.is_answer_readable:
            tally.reader_failures += 1

            def count_unreadable_page(stored: WebsiteImportDocument) -> None:
                count_skipped_page(stored)
                stored.cost_micro_usd = CostMicroUsd(
                    int(stored.cost_micro_usd) + int(cost)
                )

            progress.update(count_unreadable_page)
            return

        added: int = drafts.add(extraction.items, page.url, now)
        tally.pages_read += 1

        def count_read_page(stored: WebsiteImportDocument) -> None:
            stored.pages_read = WebsitePageCount(int(stored.pages_read) + 1)
            stored.items_found = WebsiteImportItemCount(int(stored.items_found) + added)
            stored.skipped_line_count = MenuLineCount(
                int(stored.skipped_line_count) + int(extraction.skipped_line_count)
            )
            stored.cost_micro_usd = CostMicroUsd(int(stored.cost_micro_usd) + int(cost))

        progress.update(count_read_page)

    def _allowed_kinds(self, business: BusinessDocument) -> list[KnowledgeItemKind]:
        """FAQ and policies everywhere, then the kinds the business's niche keeps."""

        niche_kinds = self._niche_template_registry.get(
            business.niche_key
        ).knowledge_kinds
        return [
            kind
            for kind in KnowledgeItemKind
            if kind in ALWAYS_ALLOWED_KINDS or kind in niche_kinds
        ]


def start_reading(stored: WebsiteImportDocument) -> None:
    """READING from the start (a repeated run starts over)."""

    stored.status = WebsiteImportStatus.READING
    stored.pages_planned = WebsitePageCount(0)
    stored.pages_read = WebsitePageCount(0)
    stored.pages_skipped = WebsitePageCount(0)
    stored.items_found = WebsiteImportItemCount(0)
    stored.skipped_line_count = MenuLineCount(0)


def count_skipped_page(stored: WebsiteImportDocument) -> None:
    stored.pages_skipped = WebsitePageCount(int(stored.pages_skipped) + 1)
