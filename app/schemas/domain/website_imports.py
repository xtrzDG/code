from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.constants.website_import import (
    WebsiteImportProblem,
    WebsiteImportStatus,
)
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.menu_import.constrained_integers import MenuLineCount
from app.schemas.typings.menu_import.prefixed_id import MenuImportBatchId
from app.schemas.typings.platform.constrained_strings import ErrorReasonDetail
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.website_import.constrained_integers import (
    WebsiteImportItemCount,
    WebsitePageCount,
)
from app.schemas.typings.website_import.prefixed_id import (
    WebsiteImportId,
    WebsiteImportRecordId,
)


class WebsiteImportDocument(BaseDocument):
    """
    The current import of a business's website into knowledge drafts.

    One per business (the id is derived from it); a new import replaces the
    last, and `import_id` names the import itself, so a job of a replaced
    import leaves the new one alone. The drafts it reads share `batch_id`
    with menu imports: the same review confirms or discards them, and none
    is used by the assistant before the owner confirms it.
    """

    id: WebsiteImportRecordId
    business_id: BusinessId
    import_id: WebsiteImportId
    batch_id: MenuImportBatchId
    url: WebLink
    status: WebsiteImportStatus
    requested_by: UserId
    pages_planned: WebsitePageCount = WebsitePageCount(0)
    pages_read: WebsitePageCount = WebsitePageCount(0)
    pages_skipped: WebsitePageCount = WebsitePageCount(0)
    items_found: WebsiteImportItemCount = WebsiteImportItemCount(0)
    skipped_line_count: MenuLineCount = MenuLineCount(0)
    cost_micro_usd: CostMicroUsd = CostMicroUsd(0)
    problem: WebsiteImportProblem | None = None
    problem_detail: ErrorReasonDetail | None = None
    started_at: Microseconds
    finished_at: Microseconds | None = None
