"""The post-call webhook: signatures, repeats, other events, metering, isolation."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.dto.channels.channel_settings import DisableChannelCommand
from tests.channels.channels_payloads import sign_elevenlabs, to_json_bytes
from tests.channels.post_call_steps import (
    post_call,
    post_call_payload,
    process_call,
    stored_calls,
)
from tests.channels.voice_setup import ASSISTANT_LINE, build_voice_setup


class TestPostCallWebhook:
    def test_repeated_webhook_is_not_billed_twice(self) -> None:
        setup = build_voice_setup()

        first = process_call(setup, post_call_payload())
        redelivered = post_call(setup, post_call_payload())
        second = process_call(setup, post_call_payload(duration=96))

        assert first["status"] == "recorded"
        # The same report again is recognised in the inbox; a changed
        # report of the call updates it without billing it twice.
        assert redelivered.json()["status"] == "duplicate"
        assert second["status"] == "duplicate"
        assert first["call_id"] == second["call_id"]
        [call] = stored_calls(setup)
        assert call.duration_seconds == 96
        assert (
            len(
                setup.testbed.usage_event_repo.list_by_business_between(
                    setup.business.id, Microseconds(0), Microseconds(2**62)
                )
            )
            == 1
        )

    @pytest.mark.parametrize(
        "variant", ["missing", "wrong_secret", "tampered", "stale", "future", "garbage"]
    )
    def test_signature_is_required(self, variant: str) -> None:
        setup = build_voice_setup()
        payload = post_call_payload()
        now: int = setup.testbed.clock.now_seconds()
        body: bytes = to_json_bytes(payload)
        signature: str | None = {
            "missing": None,
            "wrong_secret": sign_elevenlabs(body, now, secret="another"),
            "tampered": sign_elevenlabs(body + b" ", now),
            "stale": sign_elevenlabs(body, now - 31 * 60),
            "future": sign_elevenlabs(body, now + 31 * 60),
            "garbage": "t=abc,v0=",
        }[variant]

        response = post_call(setup, payload, signature=signature)

        assert response.status_code == 401
        assert stored_calls(setup) == []

    def test_slightly_old_signatures_are_accepted(self) -> None:
        setup = build_voice_setup()
        response = post_call(
            setup,
            post_call_payload(),
            signed_at=setup.testbed.clock.now_seconds() - 29 * 60,
        )
        assert response.json()["status"] == "queued"
        assert len(stored_calls(setup)) == 1

    def test_other_events_and_unknown_numbers_are_ignored(self) -> None:
        setup = build_voice_setup()

        audio = post_call(setup, post_call_payload(event_type="post_call_audio"))
        unknown_line = process_call(
            setup, post_call_payload("conv_2", agent_number="+48221234567")
        )
        no_line = process_call(setup, post_call_payload("conv_3", agent_number=None))
        foreign_agent = process_call(
            setup, post_call_payload("conv_4", agent_id="agent_of_others")
        )

        assert audio.status_code == 200
        assert audio.json()["status"] == "ignored"
        for outcome in (unknown_line, no_line, foreign_agent):
            assert outcome["status"] == "ignored"

        assert stored_calls(setup) == []

    def test_a_call_on_a_number_that_broke_is_still_stored_and_metered(
        self,
    ) -> None:
        setup = build_voice_setup()
        for channel in setup.testbed.channel_repo.list_by_business(setup.business.id):
            channel.status = ChannelStatus.ERROR
            setup.testbed.channel_repo.save(channel)

        outcome = process_call(setup, post_call_payload())

        assert outcome["status"] == "recorded"
        assert len(stored_calls(setup)) == 1
        [usage] = setup.testbed.usage_event_repo.list_by_business_between(
            setup.business.id, Microseconds(0), Microseconds(2**62)
        )
        assert usage.kind is UsageKind.VOICE_SECONDS

    def test_minutes_after_a_transfer_to_staff_are_metered(self) -> None:
        setup = build_voice_setup()
        payload = post_call_payload()
        payload["data"]["transcript"].append(
            {
                "role": "agent",
                "message": "Connecting you to a colleague.",
                "time_in_call_secs": 35,
                "tool_calls": [{"tool_name": "transfer_to_number"}],
            }
        )

        outcome = process_call(setup, payload)

        assert outcome["status"] == "recorded"
        usage = setup.testbed.usage_event_repo.list_by_business_between(
            setup.business.id, Microseconds(0), Microseconds(2**62)
        )
        assert {(event.kind, int(event.quantity)) for event in usage} == {
            (UsageKind.VOICE_SECONDS, 95),
            (UsageKind.TRANSFER_SECONDS, 60),
        }

    def test_turning_the_phone_number_off_removes_the_voice_agent(self) -> None:
        setup = build_voice_setup()
        owner_id = setup.business.members[0].user_id

        setup.testbed.disable_channel.run(
            DisableChannelCommand(
                user_id=owner_id,
                business_id=setup.business.id,
                channel=ChannelKind.PHONE,
            )
        )

        assert setup.testbed.voice_agent_removals == [setup.business.id]

    def test_malformed_reports_are_rejected(self) -> None:
        setup = build_voice_setup()
        payload = post_call_payload()
        del payload["data"]["conversation_id"]

        assert post_call(setup, payload).status_code == 422
        assert post_call(setup, {"type": "post_call_transcription"}).status_code == 422

    def test_called_number_from_dynamic_variables_and_cost_fallback(self) -> None:
        setup = build_voice_setup()
        payload = post_call_payload(
            agent_number=None,
            external_number=None,
            metadata_extra={
                "cost_fiat": None,
                "charging": {"llm_price": 0.01, "platform_price": 0.05},
            },
        )
        payload["data"]["conversation_initiation_client_data"] = {
            "dynamic_variables": {
                "system__called_number": ASSISTANT_LINE,
                "system__caller_id": "+1 202 555 0123",
            }
        }

        assert process_call(setup, payload)["status"] == "recorded"
        [call] = stored_calls(setup)
        assert call.from_phone_number == "+12025550123"
        assert call.cost_micro_usd == 60_000

    def test_tenant_isolation_between_assistant_lines(self) -> None:
        first = build_voice_setup()
        testbed = first.testbed
        other_owner = testbed.add_user("other")
        other_business = testbed.add_business(other_owner, name="Other")
        testbed.add_channel(other_business.id, ChannelKind.PHONE, "+995322111111")

        post_call(first, post_call_payload(agent_number="+995322111111"))

        assert testbed.call_repo.list_by_business(first.business.id) == []
        [other_call] = testbed.call_repo.list_by_business(other_business.id)
        assert other_call.conversation_id is None
