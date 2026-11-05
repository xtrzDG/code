"""
Website import (knowledge from the business's own site): the owner gives
the address, a worker reads up to 15 pages of the site, and the facts the
reader model finds become knowledge drafts for the same review as a menu
import. Nothing is used by the assistant before the owner confirms it.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.website_import import (
    WebsiteImportProblem,
    WebsiteImportStatus,
)
from app.schemas.dto.menu_import import ExtractedMenuItem, MenuImportResult
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.menu_import.constrained_integers import MenuLineCount
from app.schemas.typings.platform.constrained_strings import ErrorReasonDetail
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.web_fetching.constrained_strings import WebResourceUrl
from app.schemas.typings.website_import.booleans import IsReaderAnswerReadable
from app.schemas.typings.website_import.constrained_integers import (
    WebsiteImportItemCount,
    WebsitePageCount,
)
from app.schemas.typings.website_import.prefixed_id import WebsiteImportId
from app.schemas.typings.website_import.strings import (
    WebsitePageText,
    WebsitePageTitle,
)


class WebsiteImportRequest(ImmutableDTO):
    """HTTP body: the address of the business's website (its home page)."""

    url: WebLink


class StartWebsiteImportCommand(ImmutableDTO):
    """An owner or staff member asks for the business's website to be read."""

    user_id: UserId
    business_id: BusinessId
    url: WebLink


class GetWebsiteImportQuery(ImmutableDTO):
    """The business's current website import, as the cabinet shows it."""

    user_id: UserId
    business_id: BusinessId


class WebsiteImportJobPayload(ImmutableDTO):
    """Payload of the queued job that reads one website import."""

    import_id: WebsiteImportId


class WebsiteImportView(ImmutableDTO):
    """
    One website import and how far it got. `pages_planned` is 0 until the
    first page was read (then it is the number of pages the import will
    read, at most 15); `items_found` counts the drafts so far. When the
    import is done, `result` holds its drafts still waiting for review (the
    same shape as a menu import: confirm them with
    POST .../knowledge/import/confirm, discard the rest with
    DELETE .../knowledge/import/{batch_id}). A failed import names its
    `problem` and a machine-readable `problem_detail`.
    """

    id: WebsiteImportId
    business_id: BusinessId
    status: WebsiteImportStatus
    url: WebLink
    pages_planned: WebsitePageCount
    pages_read: WebsitePageCount
    pages_skipped: WebsitePageCount
    items_found: WebsiteImportItemCount
    problem: WebsiteImportProblem | None = None
    problem_detail: ErrorReasonDetail | None = None
    started_at: Microseconds
    finished_at: Microseconds | None = None
    result: MenuImportResult | None = None


class CurrentWebsiteImport(ImmutableDTO):
    """The business's latest website import, or null when it never had one."""

    current: WebsiteImportView | None = None


class SanitizedWebPage(ImmutableDTO):
    """
    A page of a website reduced to what a visitor sees: its title, its
    visible text (no scripts, styles or hidden elements) and the addresses
    it links to (absolute, as written; not yet filtered).
    """

    url: WebResourceUrl
    title: WebsitePageTitle | None = None
    text: WebsitePageText
    links: list[WebResourceUrl] = Field(default_factory=list[WebResourceUrl])


class WebsitePageExtractionRequest(ImmutableDTO):
    """
    One page for the reader model: its text, the kinds of facts the
    business keeps, and the business's currency and language.
    """

    page: SanitizedWebPage
    allowed_kinds: list[KnowledgeItemKind]
    language: LanguageTag
    currency_code: CurrencyCode


class WebsitePageExtraction(ImmutableDTO):
    """
    What the reader model found on one page, the lines it returned in an
    unusable shape, and what the call cost in tokens of `model_id`. An
    answer that is not the requested JSON at all is unreadable: no items,
    but its tokens were spent all the same.
    """

    is_answer_readable: IsReaderAnswerReadable = True
    items: list[ExtractedMenuItem] = Field(default_factory=list[ExtractedMenuItem])
    skipped_line_count: MenuLineCount = MenuLineCount(0)
    model_id: LlmModelId
    input_tokens: LlmTokenCount = LlmTokenCount(0)
    output_tokens: LlmTokenCount = LlmTokenCount(0)
