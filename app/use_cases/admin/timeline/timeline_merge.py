"""
One page of a client's story from several sources, newest first.

Some sources are read whole (a client's invoices, credit lines, product
steps: a few dozen in its life); the growing ones (the audit log, health
changes) are read a page at a time, newest before the cursor. A source
that filled its page may hold older lines it did not return, so only lines
newer than the oldest line of such a page are sure to be complete: the
page shows those, and the next page starts there. Lines of one microsecond
stay on one page.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.schemas.dto.client_story import ClientTimelineEntry, ClientTimelinePage
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.utilities.paging.cursor_paging import decode_page_cursor, encode_page_cursor

TIMELINE_CURSOR_ITEM: str = "timeline"


@dataclass(frozen=True)
class PagedLines:
    """What a growing source returned before the cursor, and whether it was
    a full page (more may be older)."""

    lines: list[ClientTimelineEntry]
    oldest: Microseconds | None
    is_full: bool


def decode_before(cursor: PageCursor | None) -> Microseconds | None:
    """The moment a page ends before; None for the first page."""

    if cursor is None:
        return None

    moment, _ = decode_page_cursor(cursor)
    return Microseconds(moment)


def merge_page(
    whole: Sequence[ClientTimelineEntry],
    paged: Sequence[PagedLines],
    before: Microseconds | None,
    size: int,
) -> ClientTimelinePage:
    candidates: list[ClientTimelineEntry] = [
        line for line in whole if before is None or int(line.occurred_at) < int(before)
    ]
    for source in paged:
        candidates.extend(source.lines)

    complete_after: int | None = max(
        (
            int(source.oldest)
            for source in paged
            if source.is_full and source.oldest is not None
        ),
        default=None,
    )
    candidates.sort(key=lambda line: -int(line.occurred_at))
    sure: list[ClientTimelineEntry] = [
        line
        for line in candidates
        if complete_after is None or int(line.occurred_at) > complete_after
    ]
    if not sure and complete_after is not None:
        # A full page of one moment: show the moment whole and go on before it.
        sure = [line for line in candidates if int(line.occurred_at) == complete_after]
        return ClientTimelinePage(
            items=sure, next_cursor=cursor_before(Microseconds(complete_after))
        )

    if len(sure) > size:
        last: int = int(sure[size - 1].occurred_at)
        page = [line for line in sure if int(line.occurred_at) >= last]
        return ClientTimelinePage(
            items=page, next_cursor=cursor_before(Microseconds(last))
        )

    if complete_after is not None:
        return ClientTimelinePage(
            items=sure, next_cursor=cursor_before(Microseconds(complete_after + 1))
        )

    return ClientTimelinePage(items=sure, next_cursor=None)


def cursor_before(moment: Microseconds) -> PageCursor:
    return encode_page_cursor(int(moment), TIMELINE_CURSOR_ITEM)
