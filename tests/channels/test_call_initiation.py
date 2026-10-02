"""Call initiation: the greeting, opening hours and whether the line answers."""

import pytest

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessStatus, Weekday
from app.schemas.constants.channels import ChannelStatus
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.profiles import BusinessProfileDocument, OpeningInterval
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.channels_payloads import to_json_bytes
from tests.channels.voice_setup import (
    ASSISTANT_LINE,
    CALLER,
    build_voice_setup,
    tool_secret,
)


class TestCallInitiation:
    def test_greeting_in_the_default_language(self) -> None:
        setup = build_voice_setup()

        response = setup.testbed.build_http_client().post(
            "/v1/voice/webhooks/conversation-initiation",
            content=to_json_bytes(
                {
                    "caller_id": CALLER,
                    "agent_id": "agent_1",
                    "called_number": ASSISTANT_LINE,
                }
            ),
            headers={
                "X-Assistant-Business-Id": str(setup.business.id),
                "X-Assistant-Tool-Secret": tool_secret(setup.business.id),
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {
                    "first_message": "[ka] AI assistant of Funicular VR.",
                    "language": "ka",
                }
            },
            # No opening hours in the profile: never put through to staff.
            # The caller's contact has no verified phone yet: not known.
            "dynamic_variables": {
                "is_open_now": "no",
                "local_now": "Thursday 2026-10-01 16:00",
                "next_days": "Fri 2026-10-02, Sat 2026-10-03, Sun 2026-10-04, "
                "Mon 2026-10-05, Tue 2026-10-06, Wed 2026-10-07, Thu 2026-10-08",
                "timezone": "Asia/Tbilisi",
                "caller_name": "unknown",
                "upcoming_booking": "none",
            },
        }
        [greeting_request] = setup.testbed.call_greeting.requests
        assert greeting_request.business_id == setup.business.id
        assert greeting_request.language is None

    @pytest.mark.parametrize(
        "switch_off",
        ["pause", "chat_plan", "version_without_voice", "number_disconnected"],
    )
    def test_no_call_is_answered_while_the_phone_assistant_is_off(
        self, switch_off: str
    ) -> None:
        setup = build_voice_setup()
        testbed = setup.testbed
        if switch_off == "pause":
            setup.business.status = BusinessStatus.PAUSED
        elif switch_off == "chat_plan":
            setup.business.plan_key = PlanKey.CHAT
        elif switch_off == "version_without_voice":
            version = testbed.assistant_version_repo.get(
                setup.business.id, setup.conversation.assistant_version_id
            )
            assert version is not None
            version.is_voice_enabled = False
            testbed.assistant_version_repo.save(version)
        else:
            for channel in testbed.channel_repo.list_by_business(setup.business.id):
                channel.status = ChannelStatus.DISABLED
                testbed.channel_repo.save(channel)

        testbed.business_repo.save(setup.business)
        response = testbed.build_http_client().post(
            "/v1/voice/webhooks/conversation-initiation",
            content=to_json_bytes({"caller_id": CALLER, "agent_id": "agent_1"}),
            headers={
                "X-Assistant-Business-Id": str(setup.business.id),
                "X-Assistant-Tool-Secret": tool_secret(setup.business.id),
            },
        )

        assert response.status_code == 409, response.text
        assert testbed.call_greeting.requests == []

    @pytest.mark.parametrize(
        ("opens", "closes", "expected"),
        [(0, 1440, "yes"), (0, 1, "no")],
    )
    def test_the_agent_learns_whether_the_business_is_open_now(
        self, opens: int, closes: int, expected: str
    ) -> None:
        setup = build_voice_setup()
        setup.testbed.profile_repo.save(
            BusinessProfileDocument(
                business_id=setup.business.id,
                niche_key=NicheKey.ENTERTAINMENT,
                answers_language=LanguageTag("ka"),
                hours=[
                    OpeningInterval(
                        weekday=weekday,
                        opens_at=OpeningMinuteOfDay(opens),
                        closes_at=ClosingMinuteOfDay(closes),
                    )
                    for weekday in Weekday
                ],
            )
        )

        response = setup.testbed.build_http_client().post(
            "/v1/voice/webhooks/conversation-initiation",
            content=to_json_bytes({"caller_id": CALLER, "agent_id": "agent_1"}),
            headers={
                "X-Assistant-Business-Id": str(setup.business.id),
                "X-Assistant-Tool-Secret": tool_secret(setup.business.id),
            },
        )

        assert response.json()["dynamic_variables"]["is_open_now"] == expected

    def test_initiation_needs_the_business_secret(self) -> None:
        setup = build_voice_setup()

        response = setup.testbed.build_http_client().post(
            "/v1/voice/webhooks/conversation-initiation",
            content=b"{}",
            headers={"X-Assistant-Business-Id": str(setup.business.id)},
        )

        assert response.status_code == 401
