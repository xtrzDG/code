"""
An owner's edit never leaves the meaning side of the search behind: a
vector computed from an item's old text is ignored until the item is
indexed again, and creating, editing or deleting an item queues that
indexing.
"""

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    DeleteKnowledgeItemCommand,
    KnowledgeItemInput,
    KnowledgeItemPatch,
    UpdateKnowledgeItemCommand,
)
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.use_cases.knowledge.create_knowledge_item_use_case import (
    CreateKnowledgeItemUseCase,
)
from app.use_cases.knowledge.delete_knowledge_item_use_case import (
    DeleteKnowledgeItemUseCase,
)
from app.use_cases.knowledge.update_knowledge_item_use_case import (
    UpdateKnowledgeItemUseCase,
)
from app.use_cases.shared.knowledge_index_queue import INDEX_KNOWLEDGE_JOB
from tests.knowledge.cross_language.world import CrossLanguageWorld
from tests.knowledge.website_import.recording_job_queue import RecordingJobQueue

PARKING_IN_RUSSIAN = "Где оставить машину?"


def test_a_vector_of_an_items_old_text_is_ignored_until_it_is_indexed_again() -> None:
    world = CrossLanguageWorld()
    item = world.add_item("Do you have parking?", body="The city lot is next door.")
    world.run_index()
    assert world.search(PARKING_IN_RUSSIAN, "ru") == ["Do you have parking?"]

    world.knowledge_item_repo.save(
        item.model_copy(
            update={
                "title": KnowledgeTitle("Do you deliver?"),
                "body": KnowledgeBody("Through Wolt and Glovo."),
                "aliases": [],
            }
        )
    )

    assert world.search(PARKING_IN_RUSSIAN, "ru") == []

    world.run_index()
    assert world.search("Есть ли доставка?", "ru") == ["Do you deliver?"]


def test_creating_editing_and_deleting_an_item_queue_its_indexing() -> None:
    world = CrossLanguageWorld()
    queue = RecordingJobQueue()
    create = CreateKnowledgeItemUseCase(
        business_repo=world.business_repo,
        knowledge_item_repo=world.knowledge_item_repo,
        resource_repo=world.resource_repo,
        niche_template_registry=world.niche_template_registry,
        wall_clock=world.wall_clock,
        job_queue=queue,
    )
    update = UpdateKnowledgeItemUseCase(
        business_repo=world.business_repo,
        knowledge_item_repo=world.knowledge_item_repo,
        resource_repo=world.resource_repo,
        niche_template_registry=world.niche_template_registry,
        wall_clock=world.wall_clock,
        job_queue=queue,
    )
    delete = DeleteKnowledgeItemUseCase(
        knowledge_item_repo=world.knowledge_item_repo, job_queue=queue
    )

    created = create.run(
        CreateKnowledgeItemCommand(
            business_id=world.business.id,
            item=KnowledgeItemInput(
                kind=KnowledgeItemKind.FAQ, title=KnowledgeTitle("Do you have parking?")
            ),
        )
    )
    update.run(
        UpdateKnowledgeItemCommand(
            business_id=world.business.id,
            item_id=created.id,
            patch=KnowledgeItemPatch(body=KnowledgeBody("The city lot is next door.")),
        )
    )
    delete.run(
        DeleteKnowledgeItemCommand(business_id=world.business.id, item_id=created.id)
    )

    assert [(job.name, job.business_id) for job in queue.jobs] == [
        (INDEX_KNOWLEDGE_JOB, world.business.id)
    ] * 3
    assert {str(job.serial_key) for job in queue.jobs} == {
        f"index_knowledge:{world.business.id}"
    }
