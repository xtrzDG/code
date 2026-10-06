"""
ETag and If-Match of the business settings (docs/api-versioning.md).

The ETag of a business is its revision as a strong entity tag (`"7"`), the
same number as the `revision` field of the body. A change sent with
`If-Match: "7"` applies only while the stored revision is still 7, else it
is refused with 412. `If-Match: *` accepts any revision. Comparison is
strong (RFC 9110, 13.1.1): a weak tag (`W/"7"`) or one that names no
revision never matches.
"""

import re
from typing import Annotated, Any

from fastapi import Header, Response

from app.schemas.typings.businesses.constrained_integers import BusinessRevision

ETAG_HEADER: str = "ETag"
IF_MATCH_HEADER: str = "If-Match"
ANY_ENTITY_TAG: str = "*"
# A strong entity tag that names a revision: digits in double quotes.
REVISION_TAG: re.Pattern[str] = re.compile(r'^"(\d{1,18})"$')
IF_MATCH_DESCRIPTION: str = (
    "Optional. The ETag of the business this change was made from (as GET "
    'returned it, e.g. `"7"`), or `*`. When the business was saved since, '
    "nothing changes and the answer is 412 with the reason "
    "`precondition_failed`. The body's `expected_revision` is the same "
    "check answered with 409."
)
ETAG_RESPONSE_HEADER: dict[str, Any] = {
    ETAG_HEADER: {
        "description": (
            'The business revision as a strong entity tag (`"7"`); send it '
            "back as If-Match with a change."
        ),
        "schema": {"type": "string"},
    }
}

type IfMatchHeader = Annotated[
    str | None,
    Header(alias=IF_MATCH_HEADER, description=IF_MATCH_DESCRIPTION),
]


def revision_entity_tag(revision: BusinessRevision) -> str:
    """The strong entity tag of a business revision: `"7"`."""

    return f'"{int(revision)}"'


def tag_response_with_revision(response: Response, revision: BusinessRevision) -> None:
    response.headers[ETAG_HEADER] = revision_entity_tag(revision)


def read_if_match_revisions(if_match: str | None) -> list[BusinessRevision] | None:
    """
    The revisions an If-Match header accepts: None without the header or
    with `*` (any revision); otherwise the revisions its strong tags name,
    which is empty (nothing matches) when it has none.
    """

    if if_match is None:
        return None

    tags: list[str] = [tag.strip() for tag in if_match.split(",")]
    if ANY_ENTITY_TAG in tags:
        return None

    return [revision for tag in tags if (revision := revision_of_tag(tag)) is not None]


def revision_of_tag(tag: str) -> BusinessRevision | None:
    matched: re.Match[str] | None = REVISION_TAG.match(tag)
    if matched is None:
        return None

    # At most 18 digits: a non-negative 64-bit number, always a revision.
    return BusinessRevision(int(matched.group(1)))
