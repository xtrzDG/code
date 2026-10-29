"""
The few S3 XML replies the backup bucket client reads.

S3's replies are flat and their values are escaped XML text, so a pattern
per element is enough; no XML parser runs on remote input (no entity
expansion, nothing to configure safely).
"""

import html
import re
from dataclasses import dataclass

CONTENTS_PATTERN: re.Pattern[str] = re.compile(r"<Contents>(.*?)</Contents>", re.S)


@dataclass(frozen=True)
class ListedObject:
    key: str
    size: int


@dataclass(frozen=True)
class ListingPage:
    objects: list[ListedObject]
    next_token: str | None


def element_text(xml_text: str, element: str) -> str | None:
    """The unescaped text of the first `<element>`, or None."""

    match = re.search(rf"<{element}>(.*?)</{element}>", xml_text, re.S)
    return None if match is None else html.unescape(match.group(1))


def read_listing_page(xml_text: str) -> ListingPage:
    """A ListObjectsV2 page: its objects and the token of the next page."""

    objects: list[ListedObject] = []
    for block in CONTENTS_PATTERN.findall(xml_text):
        key: str | None = element_text(block, "Key")
        size_text: str | None = element_text(block, "Size")
        if key is not None:
            objects.append(
                ListedObject(
                    key=key,
                    size=int(size_text) if size_text and size_text.isdigit() else 0,
                )
            )

    is_truncated: bool = (element_text(xml_text, "IsTruncated") or "") == "true"
    next_token: str | None = (
        element_text(xml_text, "NextContinuationToken") if is_truncated else None
    )
    return ListingPage(objects=objects, next_token=next_token)


def read_error_code(xml_text: str) -> str | None:
    """The `<Code>` of an S3 error reply (AccessDenied, NoSuchBucket, ...)."""

    if "<Error>" not in xml_text:
        return None

    code: str | None = element_text(xml_text, "Code")
    return code if code is not None and code.isalnum() else None


def build_completion(etags: list[str]) -> bytes:
    """The CompleteMultipartUpload body: every part's number and ETag."""

    parts: str = "".join(
        f"<Part><PartNumber>{number}</PartNumber>"
        f"<ETag>{html.escape(etag)}</ETag></Part>"
        for number, etag in enumerate(etags, start=1)
    )
    return f"<CompleteMultipartUpload>{parts}</CompleteMultipartUpload>".encode()
