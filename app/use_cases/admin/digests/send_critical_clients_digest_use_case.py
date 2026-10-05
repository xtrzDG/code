from contextlib import AbstractContextManager, nullcontext

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.client_care_repositories import (
    AdminDigestStateRepoContract,
    ClientHealthChangeRepoContract,
)
from app.contracts.repositories.client_standing_repositories import (
    ClientStandingRepoContract,
)
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.platform_alert_settings import PlatformAlertSettings
from app.schemas.constants.client_health import AdminDigestKind, ClientHealthStatus
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.client_health_changes import (
    AdminDigestStateDocument,
    ClientHealthChangeDocument,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.platform_alerts import PlatformAlertDelivery
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.strings import ManagerContactAddress
from app.schemas.typings.monitoring.strings import PlatformAlertMessage
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.admin.alerts.check_platform_alerts_use_case import (
    SEND_PLATFORM_ALERT_JOB,
    recipient_serial_key,
)
from app.use_cases.admin.digests.critical_digest_texts import compose_critical_digest

MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000


class SendCriticalClientsDigestUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The `critical_clients_digest` periodic job (once a day, one worker): the
    clients whose health turned CRITICAL since the last digest and are
    still critical now go to the platform team's Telegram chats through the
    platform bot (PLATFORM_ALERT_TELEGRAM_CHAT_IDS), one message per chat,
    as `send_platform_alert` jobs of the outbound lane (retried with
    backoff). A client that recovered meanwhile is left out; a day without
    news sends nothing.

    The digest remembers how far it looked (`admin_digest_states`), so a
    day the worker missed is told the next day and nothing twice; the first
    digest looks one day back. The state and the queued messages are
    stored together. The report counts the messages queued.
    """

    def __init__(
        self,
        health_change_repo: ClientHealthChangeRepoContract,
        client_standing_repo: ClientStandingRepoContract,
        digest_state_repo: AdminDigestStateRepoContract,
        job_queue: JobQueueFacilitatorContract,
        alert_settings: PlatformAlertSettings,
        cabinet_base_url: CabinetBaseUrl | None,
        wall_clock: WallClock[Microseconds],
        unit_of_work: StorageUnitOfWorkContract | None = None,
    ) -> None:
        self._health_change_repo: ClientHealthChangeRepoContract = health_change_repo
        self._client_standing_repo: ClientStandingRepoContract = client_standing_repo
        self._digest_state_repo: AdminDigestStateRepoContract = digest_state_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._alert_settings: PlatformAlertSettings = alert_settings
        self._cabinet_base_url: CabinetBaseUrl | None = cabinet_base_url
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work

    def run(self, input_data: JobTick) -> JobReport:
        now: Microseconds = self._wall_clock.now_unix()
        state: AdminDigestStateDocument | None = self._digest_state_repo.get(
            AdminDigestKind.CRITICAL_CLIENTS
        )
        since: Microseconds = (
            Microseconds(int(now) - MICROSECONDS_PER_DAY)
            if state is None
            else state.covered_until
        )
        latest: dict[BusinessId, ClientHealthChangeDocument] = {}
        for change in self._health_change_repo.list_changes_to(
            ClientHealthStatus.CRITICAL, since, now
        ):
            known = latest.get(change.business_id)
            if known is None or int(change.changed_at) > int(known.changed_at):
                latest[change.business_id] = change

        standings = self._client_standing_repo.get_many(sorted(latest, key=str))
        still_critical = [
            (standing, latest[business_id].issues)
            for business_id, standing in standings.items()
            if standing.health_status is ClientHealthStatus.CRITICAL
        ]
        queued: int = 0
        with self._transaction():
            if still_critical:
                queued = self._queue(
                    compose_critical_digest(still_critical, self._cabinet_base_url)
                )

            self._digest_state_repo.save(
                AdminDigestStateDocument(
                    kind=AdminDigestKind.CRITICAL_CLIENTS,
                    covered_until=now,
                    last_sent_at=now if queued else last_sent_of(state),
                    created_at=now if state is None else state.created_at,
                    updated_at=now,
                )
            )

        return JobReport(processed_count=ProcessedItemCount(queued))

    def _queue(self, text: PlatformAlertMessage) -> int:
        chats = self._alert_settings.telegram_chat_ids
        for chat_id in chats:
            delivery = PlatformAlertDelivery(
                channel=ManagerContactChannel.TELEGRAM,
                address=ManagerContactAddress(str(chat_id)),
                text=text,
            )
            self._job_queue.enqueue(
                SEND_PLATFORM_ALERT_JOB,
                JobPayloadJson(delivery.model_dump_json()),
                None,
                lane=JobLane.OUTBOUND,
                serial_key=recipient_serial_key(
                    ManagerContactChannel.TELEGRAM, str(chat_id)
                ),
            )

        return len(chats)

    def _transaction(self) -> AbstractContextManager[None]:
        if self._unit_of_work is None:
            return nullcontext()

        return self._unit_of_work.unit_of_work()


def last_sent_of(state: AdminDigestStateDocument | None) -> Microseconds | None:
    return None if state is None else state.last_sent_at
