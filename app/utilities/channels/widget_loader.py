"""
The website chat's loader (OWASP ASVS V3.6.1, PCI DSS SAQ A script
integrity): the small script an embed code points at, served from a
versioned address that never changes (`/widget/v/<hash>.js`, cached for a
year) and pinned in the embed code by its Subresource Integrity hash. A
changed byte on the way, in a cache or on a mirror, and the browser does
not run it.

The loader only adds the current widget (`/widget.js`, next to its
`/widget/v/` folder) with the embed tag's `data-*` settings, so the widget
keeps updating with every deploy while the pinned file stays the same.
Its source (`widget_loader.js`) must never change once published: a new
loader is a new file whose old version stays served (listed by
`published_widget_loaders`), because every embed code already pasted
names the old address and hash.
"""

import base64
import hashlib
from dataclasses import dataclass
from functools import cache
from pathlib import Path

LOADER_SOURCE_FILE: Path = Path(__file__).with_name("widget_loader.js")
WIDGET_LOADER_FOLDER: str = "/widget/v/"
# Hex digits of the SHA-256 of the loader in its file name.
VERSION_HEX_LENGTH: int = 16
INTEGRITY_ALGORITHM: str = "sha384"


@dataclass(frozen=True)
class WidgetLoader:
    """One published loader: its bytes, its address and its integrity hash."""

    body: bytes
    path: str
    integrity: str


def describe_loader(body: bytes) -> WidgetLoader:
    version: str = hashlib.sha256(body).hexdigest()[:VERSION_HEX_LENGTH]
    digest: bytes = hashlib.sha384(body).digest()
    return WidgetLoader(
        body=body,
        path=f"{WIDGET_LOADER_FOLDER}{version}.js",
        integrity=f"{INTEGRITY_ALGORITHM}-{base64.b64encode(digest).decode('ascii')}",
    )


@cache
def current_widget_loader() -> WidgetLoader:
    """The loader new embed codes point at."""

    return describe_loader(LOADER_SOURCE_FILE.read_bytes())


@cache
def published_widget_loaders() -> dict[str, WidgetLoader]:
    """Every loader an embed code may name, by its path (only one so far)."""

    loader: WidgetLoader = current_widget_loader()
    return {loader.path: loader}
