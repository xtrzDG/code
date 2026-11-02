"""
Aliases while a platform brake holds: the editor's "Suggest translations"
is refused, and the index job asks no model but keeps its vectors current
and is retried, as after a failed call.
"""

import pytest

from app.schemas.constants.spend import PlatformBrake
from app.schemas.dto.knowledge_aliases import SuggestKnowledgeAliasesCommand
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
)
from tests.knowledge.cross_language.world import CrossLanguageWorld


@pytest.mark.parametrize("brake", list(PlatformBrake))
def test_the_owner_s_suggestion_is_refused_while_a_brake_holds(
    brake: PlatformBrake,
) -> None:
    world = CrossLanguageWorld()
    item = world.add_item("Do you have parking?")
    world.platform_brakes.brake = brake
    command = SuggestKnowledgeAliasesCommand(
        user_id=world.owner_id, business_id=world.business.id, item_id=item.id
    )

    with pytest.raises(ConflictError) as refusal:
        world.suggest_aliases.run(command)

    assert [str(reason.code) for reason in refusal.value.reasons] == ["platform_brake"]
    assert world.suggester.requests == []
    world.platform_brakes.brake = None
    assert world.suggest_aliases.run(command).aliases != []


def test_the_index_job_names_nothing_but_keeps_vectors_and_is_retried() -> None:
    world = CrossLanguageWorld()
    parking = world.add_item("Do you have parking?")
    world.platform_brakes.brake = PlatformBrake.PAUSED

    with pytest.raises(ExternalServiceError):
        world.run_index()

    assert world.suggester.requests == []
    assert set(world.embedding_store.read_fingerprints(world.business.id)) == {
        parking.id
    }
    last = world.run_index(is_final_attempt=True)
    assert (int(last.processed_count), world.item(parking).aliases) == (0, [])
    world.platform_brakes.brake = None
    world.run_index()
    assert len(world.suggester.requests) == 1
    assert world.item(parking).aliases != []


def test_a_knowledge_base_with_nothing_to_name_reads_no_brake() -> None:
    world = CrossLanguageWorld(languages=("en",))
    world.add_item("Do you have parking?")
    world.platform_brakes.brake = PlatformBrake.BUDGET_STOP

    report = world.run_index()

    assert int(report.processed_count) == 1
    assert world.platform_brakes.readings == []
