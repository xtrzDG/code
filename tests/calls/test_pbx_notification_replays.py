"""
Zadarma's signature has no timestamp and leaves the call id out: a signed
notification whose call_start is not recent is refused, and a copy of one
under another call id is acknowledged and ignored, while the provider's
own repeat of the very same notification stays a "duplicate".
"""

import pytest

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.adapters.voice.zadarma_replay_guard import ZadarmaReplayGuard
from app.utilities.calls.zadarma_notifications import (
    CALL_START_LEAD_SECONDS,
    CALL_START_MAX_AGE_SECONDS,
    is_recent_call_start,
    read_call_start_seconds,
)
from tests.calls.call_steps import missed_calls, whatsapp_templates, zadarma_form
from tests.calls.test_pbx_notifications import notify, setup
from tests.channels.voice_setup import VoiceSetup

__all__ = ["setup"]

NOW: int = 1_790_856_000  # 2026-10-01 12:00:00 UTC, the testbed's clock


class TestFreshness:
    @pytest.mark.parametrize(
        "call_start",
        ["2026-09-29 12:00:00", "2026-10-03 15:20:00", "yesterday", "", "1790856000"],
    )
    def test_an_old_future_or_unreadable_call_start_is_refused(
        self, setup: VoiceSetup, call_start: str
    ) -> None:
        response = notify(setup, zadarma_form(call_start=call_start))

        assert response.status_code == 401
        assert missed_calls(setup) == []

    @pytest.mark.parametrize(
        "call_start",
        # Tokyo (UTC+9) a minute ago, Los Angeles (UTC-7) ten minutes ago.
        ["2026-10-01 20:59:00", "2026-10-01 04:50:00"],
    )
    def test_any_time_zone_of_the_pbx_is_recent(
        self, setup: VoiceSetup, call_start: str
    ) -> None:
        response = notify(setup, zadarma_form(call_start=call_start))

        assert response.status_code == 200, response.text
        assert response.json()["status"] == "recorded"

    def test_the_window_around_the_platforms_clock(self) -> None:
        assert is_recent_call_start(NOW + CALL_START_LEAD_SECONDS, NOW)
        assert not is_recent_call_start(NOW + CALL_START_LEAD_SECONDS + 1, NOW)
        assert is_recent_call_start(NOW - CALL_START_MAX_AGE_SECONDS, NOW)
        assert not is_recent_call_start(NOW - CALL_START_MAX_AGE_SECONDS - 1, NOW)
        assert read_call_start_seconds({"call_start": "2026-10-01 12:00:00"}) == NOW
        assert read_call_start_seconds({"call_start": "2026-10-01T12:00:00"}) is None


class TestReplays:
    def test_a_copy_under_another_call_id_is_ignored(self, setup: VoiceSetup) -> None:
        first = notify(setup, zadarma_form(pbx_call_id="in_1790856000.1"))
        copy = notify(setup, zadarma_form(pbx_call_id="in_1790856000.2"))

        assert first.json()["status"] == "recorded"
        assert copy.status_code == 200
        assert copy.json()["status"] == "ignored"
        assert len(missed_calls(setup)) == 1
        assert len(whatsapp_templates(setup)) == 1

    def test_a_copy_sent_again_is_still_ignored(self, setup: VoiceSetup) -> None:
        notify(setup, zadarma_form(pbx_call_id="in_1790856000.1"))

        copies = [
            notify(setup, zadarma_form(pbx_call_id="in_1790856000.2"))
            for _ in range(3)
        ]

        assert [copy.json()["status"] for copy in copies] == ["ignored"] * 3
        assert len(missed_calls(setup)) == 1
        assert len(whatsapp_templates(setup)) == 1

    def test_the_providers_repeat_is_still_a_duplicate(self, setup: VoiceSetup) -> None:
        notify(setup, zadarma_form())

        again = notify(setup, zadarma_form())

        assert again.json()["status"] == "duplicate"
        assert len(missed_calls(setup)) == 1

    def test_another_call_of_the_same_caller_is_a_new_one(
        self, setup: VoiceSetup
    ) -> None:
        notify(
            setup, zadarma_form(pbx_call_id="in_1", call_start="2026-10-01 13:50:00")
        )
        later = notify(
            setup, zadarma_form(pbx_call_id="in_2", call_start="2026-10-01 13:59:35")
        )

        assert later.json()["status"] == "recorded"
        assert len(missed_calls(setup)) == 2

    def test_the_claims_are_shared_by_every_process(self) -> None:
        buckets = InMemoryRateLimitBucketAdapter()
        one, other = ZadarmaReplayGuard(buckets), ZadarmaReplayGuard(buckets)
        fields = zadarma_form(pbx_call_id="in_1")

        assert not one.is_replay(fields, NOW)
        assert not other.is_replay(fields, NOW)
        assert other.is_replay({**fields, "pbx_call_id": "in_9"}, NOW)
        assert one.is_replay({**fields, "pbx_call_id": "in_9"}, NOW)
        assert not one.is_replay(fields, NOW)
