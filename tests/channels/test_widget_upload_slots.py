"""
An API process takes a bounded number of website chat uploads at once
(MEDIA_MAX_CONCURRENT_UPLOADS) and one client network at most two: the
next one is refused at once with 429 rather than read into memory, and a
place is given back however its upload ends. Before, every admitted
upload was read at the same time, as many as the rate limits let in.
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.facilitators.channels.widget_upload_slots_facilitator import (
    WidgetUploadSlotsFacilitator,
)
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.media.constrained_integers import (
    ConcurrentUploadLimit,
    UploadsPerAddressLimit,
)

HOME: ClientIpAddress = ClientIpAddress("198.51.100.7")
OFFICE: ClientIpAddress = ClientIpAddress("203.0.113.9")


def refused_code(slots: WidgetUploadSlotsFacilitator, address: ClientIpAddress) -> str:
    with pytest.raises(RateLimitedError) as refused, slots.hold(address):
        pass
    assert refused.value.retry_after_seconds is not None
    return str(refused.value.reasons[0].code)


class TestPlaces:
    def test_the_process_takes_its_limit_and_refuses_the_next(self) -> None:
        slots = WidgetUploadSlotsFacilitator(
            ConcurrentUploadLimit(3), UploadsPerAddressLimit(3)
        )

        with slots.hold(HOME), slots.hold(OFFICE), slots.hold(None):
            assert refused_code(slots, ClientIpAddress("192.0.2.1")) == (
                "too_many_uploads_at_once"
            )

        with slots.hold(HOME), slots.hold(HOME), slots.hold(HOME):
            pass

    def test_one_network_holds_at_most_its_share(self) -> None:
        slots = WidgetUploadSlotsFacilitator(ConcurrentUploadLimit(5))

        with slots.hold(HOME), slots.hold(HOME):
            assert refused_code(slots, HOME) == "too_many_uploads_from_address"
            with slots.hold(OFFICE):
                pass

    def test_rotating_addresses_of_one_ipv6_network_share_its_share(self) -> None:
        # Counted per /64, as the rate limits count a client network: one
        # host rotating its addresses does not get two places per address.
        slots = WidgetUploadSlotsFacilitator(ConcurrentUploadLimit(5))

        with (
            slots.hold(ClientIpAddress("2001:db8:1:2::a")),
            slots.hold(ClientIpAddress("2001:db8:1:2::b")),
        ):
            assert refused_code(slots, ClientIpAddress("2001:db8:1:2::c")) == (
                "too_many_uploads_from_address"
            )
            with slots.hold(ClientIpAddress("2001:db8:1:3::a")):
                pass

    def test_a_place_is_given_back_when_its_upload_fails(self) -> None:
        slots = WidgetUploadSlotsFacilitator(ConcurrentUploadLimit(1))

        with pytest.raises(ValueError), slots.hold(HOME):
            raise ValueError("the file did not parse")

        with slots.hold(HOME):
            pass

    def test_uploads_that_start_together_get_exactly_the_places(self) -> None:
        slots = WidgetUploadSlotsFacilitator(
            ConcurrentUploadLimit(3), UploadsPerAddressLimit(10)
        )
        contenders = 10
        start = threading.Barrier(contenders)
        all_tried = threading.Barrier(contenders)
        outcomes: list[str] = []
        outcomes_lock = threading.Lock()

        def upload(index: int) -> None:
            address = ClientIpAddress(f"192.0.2.{index}")
            start.wait()
            try:
                with slots.hold(address):
                    record("held")
                    all_tried.wait()
            except RateLimitedError:
                record("refused")
                all_tried.wait()

        def record(outcome: str) -> None:
            with outcomes_lock:
                outcomes.append(outcome)

        with ThreadPoolExecutor(max_workers=contenders) as pool:
            for future in [pool.submit(upload, index) for index in range(contenders)]:
                future.result()

        # Every contender tried while the three holders still held.
        assert sorted(outcomes) == ["held"] * 3 + ["refused"] * 7
        with slots.hold(HOME), slots.hold(OFFICE), slots.hold(None):
            pass
