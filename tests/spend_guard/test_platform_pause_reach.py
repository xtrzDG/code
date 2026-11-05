"""
What a paused platform means for customers: a chat turn asks no model and
goes to the team, the customer reading in their own language that a
colleague takes over; a call is refused at its start (the carrier then
forwards it to the staff phone); resuming lets the model answer again.
"""

import pytest

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.spend import SpendLevel
from app.schemas.dto.spend_guard import SpendCheckRequest, SpendVerdict
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.assistant_texts.notice_texts import (
    COLLEAGUE_TAKES_OVER,
)
from tests.brain.brain_orchestrators import GuardOptions
from tests.brain.brain_world import build_world
from tests.brain.business_setups import BusinessSetup
from tests.brain.engine_helpers import requests_of
from tests.brain.scripted_turns import say, scripted
from tests.channels.voice_setup import build_voice_setup
from tests.spend_guard import test_voice_caps
from tests.spend_guard.platform_brake_helpers import pause
from tests.spend_guard.spend_world import SpendWorld, build_spend_world

ITALY = BusinessSetup(
    name="Trattoria del Sole",
    country_code="IT",
    timezone="Europe/Rome",
    currency_code="EUR",
    languages=("it", "en"),
)


def test_a_paused_platform_hands_the_customer_to_the_team_in_their_language() -> None:
    spend = build_spend_world()
    pause(spend)
    world = build_world(
        scripted(say("Certo, a che ora?")),
        ITALY,
        guard=GuardOptions(spend_check=spend.check),
    )

    reply = world.send("Buongiorno, avete un tavolo per quattro stasera?")

    assert requests_of(world) == []
    assert len(world.handoffs()) == 1
    assert reply.text is not None
    # The colleague-takes-over text, resolved in the customer's language
    # (the brain world's resolver marks the language it resolved).
    assert "[it] A colleague will reply soon." in str(reply.text)
    assert COLLEAGUE_TAKES_OVER.values[LanguageTag("it")]

    pause(spend, is_paused=False)
    # Another customer (the first one's conversation is the team's now).
    answered = world.send("E domani sera?", user_id="393331234567", phone=None)

    assert len(requests_of(world)) == 1
    assert answered.text is not None and "Certo, a che ora?" in str(answered.text)


class RecordingRealCheck(UseCaseContract[SpendCheckRequest, SpendVerdict]):
    """The spend world's real check, with the requests it answered."""

    def __init__(self, world: SpendWorld) -> None:
        self._world: SpendWorld = world
        self.requests: list[SpendCheckRequest] = []

    def run(self, input_data: SpendCheckRequest) -> SpendVerdict:
        self.requests.append(input_data)
        return self._world.check.run(input_data)


def test_a_paused_platform_refuses_calls_at_their_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spend = build_spend_world()
    pause(spend)

    def real_check(level: SpendLevel) -> RecordingRealCheck:
        """The voice test's fixed check, replaced by the spend world's real one."""

        del level
        return RecordingRealCheck(spend)

    monkeypatch.setattr(test_voice_caps, "FixedSpendCheck", real_check)

    with pytest.raises(ConflictError):
        test_voice_caps.start_call(build_voice_setup(), SpendLevel.NORMAL)

    pause(spend, is_paused=False)
    answered = test_voice_caps.start_call(build_voice_setup(), SpendLevel.NORMAL)
    assert len(answered.requests) == 1
