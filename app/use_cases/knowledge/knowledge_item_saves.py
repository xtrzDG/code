"""
What creating and changing a knowledge item share: their dependencies, the
business the item belongs to, and its save once its performers are checked,
with the worker's index of its aliases and vector queued after it.
"""

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.knowledge.performer_links import check_item_performers
from app.use_cases.shared.knowledge_index_queue import queue_knowledge_index


class KnowledgeItemWrites:
    """The base of the use cases that create or change one knowledge item."""

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        wall_clock: WallClock[Microseconds],
        job_queue: JobQueueFacilitatorContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._job_queue: JobQueueFacilitatorContract = job_queue

    def _business(self, business_id: BusinessId) -> BusinessDocument:
        """The business, or NotFoundError."""

        business: BusinessDocument | None = self._business_repo.get(business_id)
        if business is None:
            raise NotFoundError(f"Business {business_id} was not found.")

        return business

    def _save_checked(self, item: KnowledgeItemDocument) -> list[ResourceDocument]:
        """
        Save the item once its performers are the business's resources, and
        queue its index (aliases and vector follow the edit in the worker).
        Returns the business's resources.
        """

        resources: list[ResourceDocument] = self._resource_repo.list_by_business(
            item.business_id
        )
        check_item_performers([item], resources)
        self._knowledge_item_repo.save(item)
        queue_knowledge_index(self._job_queue, item.business_id)
        return resources
