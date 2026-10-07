"""What the safe web fetcher is asked to read, and what it returns."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.web_fetching.constrained_floats import WebFetchTimeoutSeconds
from app.schemas.typings.web_fetching.constrained_integers import WebFetchByteLimit
from app.schemas.typings.web_fetching.constrained_strings import (
    WebCharsetName,
    WebMediaType,
    WebResourceUrl,
)

# The defaults of a fetch: 5 MB, 10 seconds in all.
DEFAULT_WEB_FETCH_BYTES: WebFetchByteLimit = WebFetchByteLimit(5 * 1024 * 1024)
DEFAULT_WEB_FETCH_SECONDS: WebFetchTimeoutSeconds = WebFetchTimeoutSeconds(10.0)


class WebFetchRequest(ImmutableDTO):
    """
    Read one resource. Only the listed media types are accepted; a body
    larger than `max_bytes` or a fetch longer than `timeout_seconds`
    (redirects included) is refused.
    """

    url: WebResourceUrl
    accepted_media_types: frozenset[WebMediaType] = Field(min_length=1)
    max_bytes: WebFetchByteLimit = DEFAULT_WEB_FETCH_BYTES
    timeout_seconds: WebFetchTimeoutSeconds = DEFAULT_WEB_FETCH_SECONDS


class FetchedWebResource(ImmutableDTO):
    """
    A resource read from a public address: where it ended up after
    redirects, its media type and charset as served, and its body.
    """

    url: WebResourceUrl
    final_url: WebResourceUrl
    media_type: WebMediaType
    charset: WebCharsetName | None = None
    body: bytes
