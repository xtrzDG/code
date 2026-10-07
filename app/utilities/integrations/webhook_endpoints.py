"""How an outbound webhook endpoint is named in the audit log and to people."""

from urllib.parse import urlsplit

from app.schemas.domain.webhooks import WebhookEndpointDocument
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.integrations.strings import WebhookEndpointName

WEBHOOK_ENDPOINT_ENTITY: AuditEntityName = AuditEntityName("webhook_endpoint")


def endpoint_name(endpoint: WebhookEndpointDocument) -> WebhookEndpointName:
    """
    The owner's note for the endpoint, else the host of its address: never
    the path or query, which may hold the receiver's own secret (a Zapier
    hook id), since the name reaches e-mail and locked screens.
    """

    if endpoint.label is not None:
        return WebhookEndpointName(str(endpoint.label))

    return WebhookEndpointName(urlsplit(str(endpoint.url)).hostname or "webhook")
