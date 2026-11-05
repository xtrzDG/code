"""
The daily digest of clients that newly turned critical: the standings job
records a client's health change, and the digest tells the team's
Telegram chats about the clients still critical, once.
"""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.client_care_repositories import AdminDigestStateRepository
from app.schemas.configurations.platform_alert_settings import PlatformAlertSettings
from app.schemas.constants.client_health import (
    AdminDigestKind,
    ClientHealthIssue,
    ClientHealthStatus,
)
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.client_health_changes import AdminDigestStateDocument
from app.schemas.dto.platform_alerts import PlatformAlertDelivery
from app.schemas.typings.monitoring.constrained_strings import AlertChatId
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.admin.digests.send_critical_clients_digest_use_case import (
    SendCriticalClientsDigestUseCase,
)
from app.use_cases.admin.refresh_client_standings_use_case import (
    RefreshClientStandingsUseCase,
)
from tests.admin_actions.action_world import ActionWorld
from tests.billing.grace_steps import end_trial, enforce
from tests.knowledge.website_import.recording_job_queue import RecordingJobQueue

CHATS: list[AlertChatId] = [AlertChatId("-1001234567890"), AlertChatId("777")]


class DigestWorld:
    def __init__(self, chats: list[AlertChatId] = CHATS) -> None:
        self.world = ActionWorld()
        testbed = self.world.testbed
        self.refresh = RefreshClientStandingsUseCase(
            testbed.business_repo,
            testbed.summarize_client,
            testbed.client_standing_repo,
            testbed.clock.wall_clock,
            client_health_change_repo=self.world.health_repo,
        )
        self.state_repo = AdminDigestStateRepository(
            InMemoryDocumentCollectionAdapter(AdminDigestStateDocument)
        )
        self.queue = RecordingJobQueue()
        self.digest = SendCriticalClientsDigestUseCase(
            self.world.health_repo,
            testbed.client_standing_repo,
            self.state_repo,
            self.queue,
            PlatformAlertSettings(telegram_chat_ids=chats),
            CabinetBaseUrl("https://app.example.com"),
            testbed.clock.wall_clock,
        )

    def run_refresh(self) -> None:
        self.world.testbed.run_job(self.refresh, "refresh_client_standings")

    def run_digest(self) -> int:
        self.world.testbed.clock.advance(hours=1)
        return self.world.testbed.run_job(self.digest, "critical_clients_digest")

    def turn_critical(self) -> None:
        """The trial ends unpaid and the grace runs out: leads only."""

        clock = self.world.testbed.clock
        clock.advance(days=14, hours=1)
        end_trial(self.world.testbed)
        clock.advance(days=7, hours=1)
        enforce(self.world.testbed)


def test_the_standings_job_records_a_change_of_health() -> None:
    digest = DigestWorld()
    digest.run_refresh()
    digest.turn_critical()

    digest.run_refresh()
    digest.run_refresh()

    [change] = digest.world.health_repo.list_before(
        digest.world.business.id, None, DocumentQueryLimit(10)
    )
    assert change.status is ClientHealthStatus.CRITICAL
    assert change.previous_status is not ClientHealthStatus.CRITICAL
    assert ClientHealthIssue.LEADS_ONLY_MODE in change.issues


def test_the_digest_tells_every_chat_once_about_a_client_still_critical() -> None:
    digest = DigestWorld()
    digest.run_refresh()
    digest.turn_critical()
    digest.run_refresh()

    assert digest.run_digest() == 2
    assert digest.run_digest() == 0

    deliveries = [
        PlatformAlertDelivery.model_validate_json(str(job.payload))
        for job in digest.queue.jobs
    ]
    assert [str(delivery.address) for delivery in deliveries] == [
        "-1001234567890",
        "777",
    ]
    assert {delivery.channel for delivery in deliveries} == {
        ManagerContactChannel.TELEGRAM
    }
    assert {job.lane for job in digest.queue.jobs} == {JobLane.OUTBOUND}
    text = str(deliveries[0].text)
    assert text.startswith("Clients that turned critical since the last digest: 1")
    assert "• Trattoria (GE): " in text
    assert "leads only" in text
    assert f"https://app.example.com/admin/clients/{digest.world.business.id}" in text
    state = digest.state_repo.get(AdminDigestKind.CRITICAL_CLIENTS)
    assert state is not None and state.last_sent_at is not None


def test_a_client_that_recovered_before_the_digest_is_left_out() -> None:
    digest = DigestWorld()
    digest.run_refresh()
    digest.turn_critical()
    digest.run_refresh()
    standing = digest.world.testbed.client_standing_repo.get_many(
        [digest.world.business.id]
    )[digest.world.business.id]
    standing.health_status = ClientHealthStatus.HEALTHY
    digest.world.testbed.client_standing_repo.save_many([standing])

    assert digest.run_digest() == 0
    assert digest.queue.jobs == []


def test_without_chats_nothing_is_queued_but_the_digest_moves_on() -> None:
    digest = DigestWorld(chats=[])
    digest.run_refresh()
    digest.turn_critical()
    digest.run_refresh()

    assert digest.run_digest() == 0
    state = digest.state_repo.get(AdminDigestKind.CRITICAL_CLIENTS)
    assert state is not None
    assert state.covered_until == digest.world.testbed.clock.now()
