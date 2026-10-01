"""Query parameters `limit` and `cursor` of paged cabinet lists."""

from pydantic import ValidationError

from app.schemas.dto.paging import DEFAULT_PAGE_SIZE, PageRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.platform.constrained_strings import PageCursor


def parse_page_request(raw_limit: str | None, raw_cursor: str | None) -> PageRequest:
    """`?limit=N&cursor=…` as a page request; 422 for values out of range."""

    size: PageSize = DEFAULT_PAGE_SIZE
    if raw_limit is not None:
        try:
            size = PageSize(int(raw_limit))
        except ValueError as error:
            raise ValidationFailedError(
                f"limit must be a whole number from {PageSize.ge} to {PageSize.le}."
            ) from error

    cursor: PageCursor | None = None
    if raw_cursor is not None and raw_cursor != "":
        try:
            cursor = PageCursor(raw_cursor)
        except (ValueError, ValidationError) as error:
            raise ValidationFailedError(
                "The page cursor is not valid. Load the list again."
            ) from error

    return PageRequest(size=size, cursor=cursor)
