import httpx

from app.contracts.client_contract import ClientContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret

INGESTION_PATH: str = "/api/public/ingestion"
REQUEST_TIMEOUT_SECONDS: float = 5.0


class LangfuseIngestionClient(ClientContract):
    """
    Minimal client of the Langfuse public ingestion API.

    Sends a batch of events with HTTP basic auth (public key, secret key).
    """

    def __init__(
        self,
        host: PublicBaseUrl,
        public_key: PlatformIdentifier,
        secret_key: PlatformSecret,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http_client: httpx.Client = httpx.Client(
            base_url=str(host).rstrip("/"),
            auth=(str(public_key), str(secret_key)),
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )

    def ingest(self, events: list[dict[str, object]]) -> None:
        """Send events; raises ExternalServiceError on transport or HTTP errors."""

        if not events:
            return

        try:
            response: httpx.Response = self._http_client.post(
                INGESTION_PATH,
                json={"batch": events},
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"Langfuse ingestion failed: {type(error).__name__}."
            ) from error

        if response.status_code >= 400:
            raise ExternalServiceError(
                f"Langfuse ingestion returned HTTP {response.status_code}."
            )
