"""Reading the menu behind a link, through the safe fetcher (SSRF guard)."""

from pydantic import ValidationError

from app.adapters.llm.menu_extraction.menu_link_problems import link_problem
from app.adapters.llm.menu_extraction.menu_media_content import (
    SUPPORTED_MEDIA_TYPES,
)
from app.contracts.web_fetching import SafeHttpFetcherContract
from app.schemas.constants.menu_import import MenuLinkProblem
from app.schemas.constants.web_fetching import (
    REFUSED_FETCH_PROBLEMS,
    UNUSABLE_FETCH_PROBLEMS,
    WebFetchProblem,
)
from app.schemas.dto.web_fetching import FetchedWebResource, WebFetchRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.web_fetching.constrained_integers import WebFetchByteLimit
from app.schemas.typings.web_fetching.constrained_strings import (
    WebMediaType,
    WebResourceUrl,
)

MENU_LINK_MEDIA_TYPES: frozenset[WebMediaType] = frozenset(
    WebMediaType(media_type) for media_type in SUPPORTED_MEDIA_TYPES
)
# A menu PDF or photo may be larger than a web page.
MAX_MENU_LINK_BYTES: WebFetchByteLimit = WebFetchByteLimit(10 * 1024 * 1024)


def read_menu_link(fetcher: SafeHttpFetcherContract, url: WebLink) -> tuple[str, bytes]:
    """
    The media type and body of the menu behind a public link.

    Raises:
        ValidationFailedError: with a MenuLinkProblem reason when the link
            is refused, cannot be fetched or is not a photo, PDF, text or
            web page.
    """

    try:
        resource: FetchedWebResource = fetcher.fetch(
            WebFetchRequest(
                url=WebResourceUrl(str(url)),
                accepted_media_types=MENU_LINK_MEDIA_TYPES,
                max_bytes=MAX_MENU_LINK_BYTES,
            )
        )
    except (ValidationError, ValueError) as error:
        raise link_problem(
            MenuLinkProblem.INVALID,
            "The menu link must be an http(s) address.",
            WebFetchProblem.NOT_HTTP.value,
        ) from error
    except WebFetchError as error:
        raise menu_link_problem_of(error) from error

    return str(resource.media_type), resource.body


def menu_link_problem_of(error: WebFetchError) -> ValidationFailedError:
    """The fetcher's problem as the menu import's 422 reason."""

    problem: MenuLinkProblem = MenuLinkProblem.UNREACHABLE
    if error.problem in REFUSED_FETCH_PROBLEMS:
        problem = MenuLinkProblem.INVALID
    elif error.problem in UNUSABLE_FETCH_PROBLEMS:
        problem = MenuLinkProblem.UNREADABLE

    return link_problem(problem, f"The menu link cannot be read: {error}", error.detail)
