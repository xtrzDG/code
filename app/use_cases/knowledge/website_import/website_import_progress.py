"""Recording how far a website import got, and telling the open cabinets."""

from collections.abc import Callable

from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.website_import_repositories import (
    WebsiteImportRepoContract,
)
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.website_import import (
    WebsiteImportProblem,
    WebsiteImportStatus,
)
from app.schemas.domain.website_imports import WebsiteImportDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import ErrorReasonDetail
from app.schemas.typings.website_import.prefixed_id import WebsiteImportId

FINISHED_STATUSES: frozenset[WebsiteImportStatus] = frozenset(
    {WebsiteImportStatus.DONE, WebsiteImportStatus.FAILED}
)


class WebsiteImportProgress:
    """
    Changes one import (only while it is still the business's current one
    and not finished) and announces each change as a
    `knowledge_import.progress` live event.
    """

    def __init__(
        self,
        website_import_repo: WebsiteImportRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        business_id: BusinessId,
        import_id: WebsiteImportId,
    ) -> None:
        self._website_import_repo: WebsiteImportRepoContract = website_import_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._business_id: BusinessId = business_id
        self._import_id: WebsiteImportId = import_id

    def now(self) -> Microseconds:
        return self._wall_clock.now_unix()

    def update(
        self, change: Callable[[WebsiteImportDocument], None]
    ) -> WebsiteImportDocument | None:
        """The import after `change`, or None when it was replaced or finished."""

        now: Microseconds = self.now()

        def apply(stored: WebsiteImportDocument) -> bool:
            if stored.status in FINISHED_STATUSES:
                return False

            change(stored)
            stored.updated_at = now
            return True

        changed: WebsiteImportDocument | None = self._website_import_repo.change(
            self._business_id, self._import_id, apply
        )
        if changed is not None:
            self._live_events.publish(
                self._business_id,
                LiveEventKind.KNOWLEDGE_IMPORT_PROGRESS,
                [self._import_id],
            )

        return changed

    def finish(
        self,
        problem: WebsiteImportProblem | None = None,
        detail: ErrorReasonDetail | None = None,
    ) -> None:
        """DONE, or FAILED with its problem."""

        now: Microseconds = self.now()

        def close(stored: WebsiteImportDocument) -> None:
            stored.status = (
                WebsiteImportStatus.DONE
                if problem is None
                else WebsiteImportStatus.FAILED
            )
            stored.problem = problem
            stored.problem_detail = detail
            stored.finished_at = now

        self.update(close)
