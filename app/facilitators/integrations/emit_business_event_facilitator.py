"""Announced changes become webhook deliveries (the outbox of webhooks)."""

import logging
from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager, nullcontext

from base_typed_id import BasePrefixedTypedId
from pydantic import ValidationError
from typed_time_provider import Microseconds, WallClock

from app.contracts.integrations import (
    BusinessEventObserverContract,
    PublicRecordReaderContract,
)
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.integration_repositories import (
    WebhookDeliveryRepoContract,
    WebhookEndpointRepoContract,
)
from app.contracts.storage import StorageScopeContract, StorageUnitOfWorkContract
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.storage import StorageScopeKind
from app.schemas.domain.webhooks import WebhookDeliveryDocument, WebhookEndpointDocument
from app.schemas.dto.integrations.business_events import BusinessEvent
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.integrations.strings import WebhookPayloadJson
from app.utilities.integrations.business_event_keys import (
    EVENTS_OF_CHANGE,
    business_event_id,
    webhook_delivery_id,
)
from app.utilities.integrations.event_subjects import EventSubject, read_event_subject
from app.utilities.integrations.public_timestamps import utc_timestamp
from app.utilities.integrations.webhook_jobs import (
    DELIVER_WEBHOOK_JOB,
    encode_webhook_job,
)
from app.utilities.integrations.webhook_schedule import expiry_moment, give_up_moment

LOGGER: logging.Logger = logging.getLogger(__name__)


class EmitBusinessEventFacilitator(BusinessEventObserverContract):
    """
    Subscribed to the event publisher: a change that a webhook of the
    business subscribed to (a booking made, changed or cancelled, a lead,
    a handoff, a conversation started, a call finished) is read once in its
    public shape, with the customer and the acquisition source, and queued
    for every such ACTIVE endpoint as a delivery with its job, in one
    storage transaction (the outbox: a delivery is never queued without its
    job, nor a job without its delivery). A business without webhooks pays
    one indexed read per such change; the cabinet's other changes (new
    messages, notes) are not looked at. A failure is logged and swallowed,
    in a savepoint of the change's own transaction, so it never undoes the
    change.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        endpoint_repo: WebhookEndpointRepoContract,
        delivery_repo: WebhookDeliveryRepoContract,
        record_reader: PublicRecordReaderContract,
        job_queue: JobQueueFacilitatorContract,
        unit_of_work: StorageUnitOfWorkContract | None,
        storage_scope: StorageScopeContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._delivery_repo: WebhookDeliveryRepoContract = delivery_repo
        self._record_reader: PublicRecordReaderContract = record_reader
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work
        self._storage_scope: StorageScopeContract = storage_scope
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def notice(
        self,
        business_id: BusinessId,
        event: LiveEventKind,
        ids: Sequence[BasePrefixedTypedId],
    ) -> None:
        if event not in EVENTS_OF_CHANGE or not ids:
            return

        try:
            with self._business_scope(business_id), self._transaction():
                self._emit(business_id, event, ids)
        except (ApplicationError, ValidationError) as error:
            LOGGER.warning(
                "Webhooks of %s for business %s were not queued: %s",
                event.value,
                business_id,
                type(error).__name__,
            )

    def _emit(
        self,
        business_id: BusinessId,
        event: LiveEventKind,
        ids: Sequence[BasePrefixedTypedId],
    ) -> None:
        candidates = set(EVENTS_OF_CHANGE[event])
        endpoints: list[WebhookEndpointDocument] = [
            endpoint
            for endpoint in self._endpoint_repo.list_active(business_id)
            if candidates.intersection(endpoint.event_types)
        ]
        business = self._business_repo.get(business_id) if endpoints else None
        if business is None:
            return

        subject: EventSubject | None = read_event_subject(
            self._record_reader, business, event, ids
        )
        if subject is None:
            return

        now: Microseconds = self._wall_clock.now_unix()
        envelope = BusinessEvent(
            id=business_event_id(business_id, subject.event_type, subject.key),
            type=subject.event_type,
            created_at=utc_timestamp(now),
            business_id=business_id,
            data=subject.data,
        )
        payload = WebhookPayloadJson(envelope.model_dump_json())
        for endpoint in endpoints:
            if subject.event_type in endpoint.event_types:
                self._queue(endpoint, envelope, payload, subject, now)

    def _queue(
        self,
        endpoint: WebhookEndpointDocument,
        envelope: BusinessEvent,
        payload: WebhookPayloadJson,
        subject: EventSubject,
        now: Microseconds,
    ) -> None:
        delivery = WebhookDeliveryDocument(
            id=webhook_delivery_id(endpoint.id, envelope.id),
            business_id=endpoint.business_id,
            endpoint_id=endpoint.id,
            event_id=envelope.id,
            event_type=envelope.type,
            payload=payload,
            contact_id=subject.contact_id,
            next_attempt_at=now,
            give_up_at=Microseconds(give_up_moment(int(now))),
            expires_at=Microseconds(expiry_moment(int(now))),
            created_at=now,
            updated_at=now,
        )
        if self._delivery_repo.insert_if_new(delivery):
            self._job_queue.enqueue(
                DELIVER_WEBHOOK_JOB,
                encode_webhook_job(delivery.business_id, delivery.id),
                delivery.business_id,
                lane=JobLane.DEFAULT,
            )

    @contextmanager
    def _business_scope(self, business_id: BusinessId) -> Iterator[None]:
        """The change's own scope, or the business's when it ran unscoped."""

        unscoped: bool = self._storage_scope.current().kind is StorageScopeKind.UNSCOPED
        with (
            self._storage_scope.scoped_to_business(business_id)
            if unscoped
            else nullcontext()
        ):
            yield

    def _transaction(self) -> AbstractContextManager[None]:
        """The deliveries and their jobs as one unit (Postgres; as is in memory)."""

        if self._unit_of_work is None:
            return nullcontext()

        return self._unit_of_work.unit_of_work()
