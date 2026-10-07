"""
One endpoint of a restaurant, the recorder of its delivery attempts and the
notice of its switch-off over the real staff alert facilitator, with
recording edges: contacts, devices, audit log and live events.
"""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.facilitators.integrations.webhook_disabled_notice_facilitator import (
    WebhookDisabledNoticeFacilitator,
)
from app.repositories.business_repositories import BusinessRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.webhook_repositories import (
    WebhookDeliveryRepository,
    WebhookEndpointRepository,
)
from app.schemas.constants.integrations import (
    BusinessEventType,
    WebhookDeliveryProblem,
    WebhookEndpointOrigin,
    WebhookEndpointStatus,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.webhooks import WebhookDeliveryDocument, WebhookEndpointDocument
from app.schemas.dto.integrations.webhook_attempts import (
    WebhookAttempt,
    WebhookPostResult,
)
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.schemas.typings.integrations.constrained_integers import (
    WebhookFailureCount,
    WebhookFailuresBeforeDisable,
)
from app.schemas.typings.integrations.constrained_strings import (
    WebhookEndpointLabel,
    WebhookSecretHint,
    WebhookTargetUrl,
)
from app.schemas.typings.integrations.prefixed_id import BusinessEventId
from app.schemas.typings.integrations.strings import WebhookPayloadJson
from app.schemas.typings.observability.constrained_integers import HttpStatusCode
from app.use_cases.integrations.record_webhook_attempt_use_case import (
    RecordWebhookAttemptUseCase,
)
from tests.channels.outbox_fakes import RecordingJobQueue
from tests.live_events.recording_event_publisher import RecordingEventPublisher
from tests.notifications.alert_world import NOON, AlertWorld
from tests.operations.fakes import FakeLocalizedTextResolver

FAILURES_BEFORE_DISABLE: int = 3
DAY_MICROSECONDS: int = 24 * 60 * 60 * 1_000_000
# A receiver's own secret sits in the path; no notice may show it.
HOOK_URL: str = "https://hooks.example.com/hooks/catch/123456/secret-hook-id/"


class NoticeWorld:
    def __init__(self, business_repo: BusinessRepoContract | None = None) -> None:
        self.alerts = AlertWorld()
        self.business: BusinessDocument = self.alerts.business
        self.minutes: int = 0
        self.business_repo = BusinessRepository(
            InMemoryDocumentCollectionAdapter(BusinessDocument)
        )
        self.business_repo.save(self.business)
        self.audit = AuditLogRepository(
            InMemoryDocumentCollectionAdapter(AuditLogEntryDocument)
        )
        self.live = RecordingEventPublisher()
        self.endpoints = WebhookEndpointRepository(
            InMemoryDocumentCollectionAdapter(WebhookEndpointDocument)
        )
        self.deliveries = WebhookDeliveryRepository(
            InMemoryDocumentCollectionAdapter(WebhookDeliveryDocument)
        )
        self.notices = WebhookDisabledNoticeFacilitator(
            business_repo=business_repo or self.business_repo,
            staff_alerts=self.alerts.alerts,
            audit_log_repo=self.audit,
            live_events=self.live,
            localized_text_resolver=FakeLocalizedTextResolver(),
        )
        self.recorder = RecordWebhookAttemptUseCase(
            delivery_repo=self.deliveries,
            endpoint_repo=self.endpoints,
            job_queue=RecordingJobQueue(),
            unit_of_work=None,
            failures_before_disable=WebhookFailuresBeforeDisable(
                FAILURES_BEFORE_DISABLE
            ),
            notices=self.notices,
            jitter=lambda: 0.5,
        )

    def now(self) -> Microseconds:
        return self.alerts.clock.wall_clock.now_unix()

    def add_endpoint(
        self,
        label: str | None = None,
        origin: WebhookEndpointOrigin = WebhookEndpointOrigin.CABINET,
    ) -> WebhookEndpointDocument:
        endpoint = WebhookEndpointDocument(
            business_id=self.business.id,
            url=WebhookTargetUrl(HOOK_URL),
            label=None if label is None else WebhookEndpointLabel(label),
            event_types=[BusinessEventType.BOOKING_CREATED],
            encrypted_secret=EncryptedChannelSecret("sealed"),
            secret_hint=WebhookSecretHint("ab12"),
            origin=origin,
            created_at=self.now(),
            updated_at=self.now(),
        )
        self.endpoints.save(endpoint)
        return endpoint

    def delivery(self, endpoint: WebhookEndpointDocument) -> WebhookDeliveryDocument:
        now: int = int(self.now())
        delivery = WebhookDeliveryDocument(
            business_id=self.business.id,
            endpoint_id=endpoint.id,
            event_id=BusinessEventId(),
            event_type=BusinessEventType.BOOKING_CREATED,
            payload=WebhookPayloadJson("{}"),
            give_up_at=Microseconds(now + DAY_MICROSECONDS),
            expires_at=Microseconds(now + 30 * DAY_MICROSECONDS),
            created_at=Microseconds(now),
            updated_at=Microseconds(now),
        )
        self.deliveries.insert_if_new(delivery)
        return delivery

    def attempt(
        self,
        delivery: WebhookDeliveryDocument,
        status_code: int = 503,
        problem: WebhookDeliveryProblem = WebhookDeliveryProblem.HTTP_STATUS,
    ) -> WebhookAttempt:
        self.minutes += 1
        self.alerts.clock.move_to(NOON + timedelta(minutes=self.minutes))
        return WebhookAttempt(
            delivery=delivery,
            result=WebhookPostResult(
                status_code=HttpStatusCode(status_code), problem=problem
            ),
            attempted_at=self.now(),
        )

    def fail(self, endpoint: WebhookEndpointDocument, times: int = 1) -> None:
        """`times` events whose first attempt fails."""

        for _ in range(times):
            self.recorder.run(self.attempt(self.delivery(endpoint)))

    def stored(self, endpoint: WebhookEndpointDocument) -> WebhookEndpointDocument:
        found = self.endpoints.get(self.business.id, endpoint.id)
        assert found is not None
        return found

    def switch_on(self, endpoint: WebhookEndpointDocument) -> None:
        """The owner switches the endpoint on again (it counts from zero)."""

        self.endpoints.update(
            self.business.id,
            endpoint.id,
            lambda current: current.model_copy(
                update={
                    "status": WebhookEndpointStatus.ACTIVE,
                    "consecutive_failures": WebhookFailureCount(0),
                    "disabled_at": None,
                }
            ),
        )

    def subjects(self) -> list[str]:
        return [
            str(notification.subject)
            for notification in self.alerts.notifier.notifications
        ]
