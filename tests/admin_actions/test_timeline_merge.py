"""The merge of a story's sources into pages, at its edges."""

from typed_time_provider import Microseconds

from app.schemas.constants.client_health import ClientTimelineEvent, ClientTimelineKind
from app.schemas.dto.client_story import ClientTimelineEntry
from app.use_cases.admin.timeline.timeline_merge import (
    PagedLines,
    cursor_before,
    decode_before,
    merge_page,
)


def line(moment: int, kind: ClientTimelineKind) -> ClientTimelineEntry:
    return ClientTimelineEntry(
        kind=kind,
        event=ClientTimelineEvent.AUDIT_ENTRY,
        occurred_at=Microseconds(moment),
    )


def test_a_full_page_of_one_moment_is_shown_whole_and_the_story_goes_on() -> None:
    same = [line(500, ClientTimelineKind.CHANGE) for _ in range(3)]

    page = merge_page(
        [line(100, ClientTimelineKind.BILLING)],
        [PagedLines(lines=same, oldest=Microseconds(500), is_full=True)],
        None,
        2,
    )

    assert [int(entry.occurred_at) for entry in page.items] == [500, 500, 500]
    assert page.next_cursor == cursor_before(Microseconds(500))
    assert decode_before(page.next_cursor) == 500


def test_a_page_keeps_the_lines_of_its_last_moment_together() -> None:
    lines = [
        line(300, ClientTimelineKind.BILLING),
        line(200, ClientTimelineKind.MILESTONE),
        line(200, ClientTimelineKind.ADMIN_ACTION),
        line(100, ClientTimelineKind.HEALTH),
    ]

    page = merge_page(lines, [], None, 2)

    assert [(int(e.occurred_at), e.kind) for e in page.items] == [
        (300, ClientTimelineKind.BILLING),
        (200, ClientTimelineKind.ADMIN_ACTION),
        (200, ClientTimelineKind.MILESTONE),
    ]
    assert decode_before(page.next_cursor) == 200
    assert merge_page(lines, [], Microseconds(200), 2).items == [lines[3]]
    assert decode_before(None) is None
