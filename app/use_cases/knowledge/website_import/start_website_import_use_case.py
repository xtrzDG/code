from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.website_import_repositories import (
    WebsiteImportRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.web_fetching import SafeHttpFetcherContract
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.website_import import WebsiteImportStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.website_imports import WebsiteImportDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.website_import import (
    StartWebsiteImportCommand,
    WebsiteImportJobPayload,
    WebsiteImportView,
)
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.menu_import.prefixed_id import MenuImportBatchId
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.strings import JobPayloadJson
from app.schemas.typings.web_fetching.constrained_strings import WebResourceUrl
from app.schemas.typings.website_import.prefixed_id import WebsiteImportId
from app.use_cases.knowledge.website_import.website_import_problems import (
    import_already_running,
    invalid_address,
)
from app.use_cases.knowledge.website_import.website_import_views import (
    build_website_import_view,
)
from app.utilities.knowledge.website.website_import_keys import (
    derive_website_import_record_id,
)
from app.utilities.knowledge.website.website_import_limits import (
    refuse_too_many_imports,
)

IMPORT_WEBSITE_JOB: JobName = JobName("import_website")
# An import that has not moved for this long is taken as abandoned.
STALE_IMPORT_MICROSECONDS: int = 15 * 60 * 1_000_000


class StartWebsiteImportUseCase(
    UseCaseContract[StartWebsiteImportCommand, WebsiteImportView]
):
    """
    Queue the reading of a business's website (owners and staff). The
    address is checked first (public http(s) on port 80/443, no intranet
    names or private addresses: the host itself is checked when the worker
    connects), then at most 10 imports per hour per business are allowed,
    and only one at a time. The worker reads the site in the default lane,
    one import per business at a time; the cabinet follows it through live
    events and GET .../knowledge/import-website/current.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        safe_http_fetcher: SafeHttpFetcherContract,
        website_import_repo: WebsiteImportRepoContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        job_queue: JobQueueFacilitatorContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._safe_http_fetcher: SafeHttpFetcherContract = safe_http_fetcher
        self._website_import_repo: WebsiteImportRepoContract = website_import_repo
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: StartWebsiteImportCommand) -> WebsiteImportView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        try:
            self._safe_http_fetcher.vet(WebResourceUrl(str(input_data.url)))
        except WebFetchError as error:
            raise invalid_address(error) from error

        now: Microseconds = self._wall_clock.now_unix()
        stale_before = Microseconds(int(now) - STALE_IMPORT_MICROSECONDS)
        current: WebsiteImportDocument | None = (
            self._website_import_repo.get_by_business(business.id)
        )
        if is_running(current, stale_before):
            raise import_already_running()

        refuse_too_many_imports(self._rate_limit_registry, business.id, now)
        website_import = WebsiteImportDocument(
            id=derive_website_import_record_id(business.id),
            business_id=business.id,
            import_id=WebsiteImportId(),
            batch_id=MenuImportBatchId(),
            url=input_data.url,
            status=WebsiteImportStatus.QUEUED,
            requested_by=input_data.user_id,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        if self._website_import_repo.start(website_import, stale_before) is not None:
            raise import_already_running()

        self._job_queue.enqueue(
            IMPORT_WEBSITE_JOB,
            JobPayloadJson(
                WebsiteImportJobPayload(
                    import_id=website_import.import_id
                ).model_dump_json()
            ),
            business.id,
            lane=JobLane.DEFAULT,
            serial_key=JobSerialKey(f"website_import:{business.id}"),
        )
        self._live_events.publish(
            business.id,
            LiveEventKind.KNOWLEDGE_IMPORT_PROGRESS,
            [website_import.import_id],
        )
        return build_website_import_view(website_import)


def is_running(
    website_import: WebsiteImportDocument | None, stale_before: Microseconds
) -> bool:
    return (
        website_import is not None
        and website_import.status
        in (WebsiteImportStatus.QUEUED, WebsiteImportStatus.READING)
        and website_import.updated_at >= stale_before
    )
