import httpx

from app.contracts.client_contract import ClientContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret

OTEL_TRACES_PATH: str = "/api/public/otel/v1/traces"
# Direct OTLP exporters send it so spans reach Langfuse's v4 data model in
# real time (the OpenAPI document's description of the endpoint).
INGESTION_VERSION_HEADERS: dict[str, str] = {"x-langfuse-ingestion-version": "4"}
INSTRUMENTATION_SCOPE: str = "assistant-workshop.quality-journal"
REQUEST_TIMEOUT_SECONDS: float = 5.0


class LangfuseIngestionClient(ClientContract):
    """
    Minimal client of Langfuse's OpenTelemetry ingestion: OTLP/HTTP with a
    JSON `ExportTraceServiceRequest` to POST /api/public/otel/v1/traces,
    HTTP basic auth (public key, secret key).

    The spans come ready in OTLP/JSON (`langfuse_otel_spans`); the client
    wraps them in one resource and one instrumentation scope.
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
            headers=INGESTION_VERSION_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )

    def ingest(self, spans: list[dict[str, object]]) -> None:
        """Send spans; raises ExternalServiceError on transport or HTTP errors."""

        if not spans:
            return

        try:
            response: httpx.Response = self._http_client.post(
                OTEL_TRACES_PATH,
                json=export_trace_request(spans),
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"Langfuse ingestion failed: {type(error).__name__}."
            ) from error

        if response.status_code >= 400:
            raise ExternalServiceError(
                f"Langfuse ingestion returned HTTP {response.status_code}."
            )


def export_trace_request(spans: list[dict[str, object]]) -> dict[str, object]:
    """The OTLP/JSON `ExportTraceServiceRequest` carrying the spans."""

    return {
        "resourceSpans": [
            {
                "resource": {"attributes": []},
                "scopeSpans": [
                    {"scope": {"name": INSTRUMENTATION_SCOPE}, "spans": spans}
                ],
            }
        ]
    }
