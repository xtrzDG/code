from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.integrations.constrained_integers import (
    PublicApiRequestsPerMinute,
    WebhookFailuresBeforeDisable,
)

DEFAULT_REQUESTS_PER_MINUTE: PublicApiRequestsPerMinute = PublicApiRequestsPerMinute(
    120
)
DEFAULT_FAILURES_BEFORE_DISABLE: WebhookFailuresBeforeDisable = (
    WebhookFailuresBeforeDisable(15)
)


class PublicApiSettings(ImmutableDTO):
    """
    The public API and outbound webhooks (docs/api-versioning.md):

    - `requests_per_minute` (PUBLIC_API_REQUESTS_PER_MINUTE, 120): what one
      API key may ask in a minute, counted for every API instance together;
      more are refused with 429 and Retry-After;
    - `webhook_failures_before_disable` (WEBHOOK_DISABLE_AFTER_FAILURES,
      15): after how many failed attempts in a row a webhook endpoint is
      switched off (its owner switches it on again in the cabinet).
    """

    requests_per_minute: PublicApiRequestsPerMinute = DEFAULT_REQUESTS_PER_MINUTE
    webhook_failures_before_disable: WebhookFailuresBeforeDisable = (
        DEFAULT_FAILURES_BEFORE_DISABLE
    )
