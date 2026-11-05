"""
The outbound lane's bulkheads, the platform alerts' own lane and the split
provider timeouts: a provider holds at most its share of the threads, the
alerts move to the ops lane once its release gate opens, and a provider
that hangs holds a thread for one read budget, not more.
"""

import smtplib
import socket
import threading
from collections.abc import Iterator

import pytest

from app.clients.email import smtp_connections
from app.clients.email.smtp_connections import open_smtp_connection
from app.clients.flitt import flitt_client
from app.clients.http.provider_timeouts import provider_timeout
from app.clients.meta import graph_api_client
from app.facilitators.resilience.outbound_bulkhead_facilitator import (
    OutboundBulkheadFacilitator,
)
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.resilience import OutboundProvider
from app.schemas.exceptions.storage_errors import ClosedReleaseGateError
from app.schemas.typings.resilience.constrained_integers import ProviderSlotCount
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.jobs.platform_alert_lane import platform_alert_lane
from app.utilities.storage.release_gates import (
    OPS_LANE_GATE,
    RELEASE_GATES,
    closed_gates_of,
    refuse_closed_values,
)

WAIT_SECONDS: float = 10.0


def test_a_provider_holds_at_most_its_slots_and_the_others_keep_theirs() -> None:
    bulkhead = OutboundBulkheadFacilitator(ProviderSlotCount(2))
    inside = threading.Barrier(3)
    let_go = threading.Event()
    taken: list[bool] = []

    def hang_in_meta() -> None:
        with bulkhead.reserve(OutboundProvider.META) as is_taken:
            taken.append(is_taken)
            inside.wait(WAIT_SECONDS)
            let_go.wait(WAIT_SECONDS)

    holders = [threading.Thread(target=hang_in_meta) for _ in range(2)]
    for holder in holders:
        holder.start()
    inside.wait(WAIT_SECONDS)

    # Both of Meta's slots are held: a third send does not wait for one.
    with bulkhead.reserve(OutboundProvider.META) as is_meta_free:
        assert is_meta_free is False
    with bulkhead.reserve(OutboundProvider.TELEGRAM) as is_telegram_free:
        assert is_telegram_free is True
    with bulkhead.reserve(OutboundProvider.PLATFORM_BOT) as is_bot_free:
        assert is_bot_free is True

    let_go.set()
    for holder in holders:
        holder.join(WAIT_SECONDS)

    assert taken == [True, True]
    with bulkhead.reserve(OutboundProvider.META) as is_meta_free_again:
        assert is_meta_free_again is True


def test_a_slot_comes_back_when_the_send_fails() -> None:
    bulkhead = OutboundBulkheadFacilitator(ProviderSlotCount(1))

    with (
        pytest.raises(TimeoutError),
        bulkhead.reserve(OutboundProvider.SMTP) as is_taken,
    ):
        assert is_taken is True
        raise TimeoutError("The mail server did not answer.")

    with bulkhead.reserve(OutboundProvider.SMTP) as is_taken_again:
        assert is_taken_again is True


def test_alerts_use_the_ops_lane_only_once_its_gate_is_open() -> None:
    opened = [
        gate.model_copy(update={"is_open": True})
        if gate.name == OPS_LANE_GATE
        else gate
        for gate in RELEASE_GATES
    ]
    queued_jobs = DocumentCollectionName("queued_jobs")

    assert platform_alert_lane() is JobLane.OUTBOUND
    assert platform_alert_lane(opened) is JobLane.OPS
    # The release that ships the lane cannot store a job in it yet: the one
    # before would not know the value.
    with pytest.raises(ClosedReleaseGateError):
        refuse_closed_values({"lane": "ops"}, closed_gates_of(queued_jobs))
    refuse_closed_values({"lane": "ops"}, closed_gates_of(queued_jobs, opened))


def test_provider_clients_connect_within_3_s_and_read_within_10_s() -> None:
    timeout = provider_timeout()

    assert (timeout.connect, timeout.read) == (3.0, 10.0)
    assert (
        graph_api_client.REQUEST_TIMEOUT.connect,
        graph_api_client.REQUEST_TIMEOUT.read,
    ) == (3.0, 10.0)
    # A payment page may take longer to create; it still connects fast.
    flitt = provider_timeout(flitt_client.READ_TIMEOUT_SECONDS)
    assert (flitt.connect, flitt.read) == (3.0, 15.0)


@pytest.fixture
def mail_server(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[float | None]]:
    """A greeting mail server on a socket pair: no network."""

    ours, theirs = socket.socketpair()
    theirs.sendall(b"220 mail.example ESMTP ready\r\n")
    connect_timeouts: list[float | None] = []

    def create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
        source_address: tuple[str, int] | None = None,
    ) -> socket.socket:
        del address, source_address
        connect_timeouts.append(timeout)
        ours.settimeout(timeout)
        return ours

    monkeypatch.setattr(socket, "create_connection", create_connection)
    yield connect_timeouts
    ours.close()
    theirs.close()


def test_smtp_connects_within_3_s_then_reads_within_10_s(
    mail_server: list[float | None],
) -> None:
    client: smtplib.SMTP = open_smtp_connection("mail.example", 587, None)

    assert mail_server == [smtp_connections.SMTP_CONNECT_TIMEOUT_SECONDS]
    assert client.timeout == smtp_connections.SMTP_READ_TIMEOUT_SECONDS
    assert client.sock is not None
    assert client.sock.gettimeout() == 10.0
