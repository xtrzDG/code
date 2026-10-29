"""The Graph API address, version and timeouts the platform's Meta clients share."""

import httpx

from app.clients.http.provider_timeouts import provider_timeout

META_GRAPH_BASE_URL: str = "https://graph.facebook.com"
# Graph API version the payloads were written against; Meta keeps a version
# working for at least two years after the next one is released.
DEFAULT_GRAPH_API_VERSION: str = "v23.0"
# Connect within 3 s, answer within 10 s (`provider_timeout`).
REQUEST_TIMEOUT: httpx.Timeout = provider_timeout()


class GraphApiClient:
    """
    The HTTP client of one Graph API client: the versioned base address and
    the providers' timeouts; requests go through `graph_requests`.
    """

    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        api_version: str = DEFAULT_GRAPH_API_VERSION,
        base_url: str = META_GRAPH_BASE_URL,
    ) -> None:
        self._http_client: httpx.Client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/{api_version}",
            timeout=REQUEST_TIMEOUT,
            transport=transport,
        )
