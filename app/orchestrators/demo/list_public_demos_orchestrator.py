import logging

from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.public_demo import (
    PublicDemoBusinessIds,
    PublicDemoCard,
    PublicDemoCardQuery,
    PublicDemoList,
    PublicDemoListQuery,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.public_site.constrained_integers import (
    PublicDemoMessagesLeft,
)
from app.utilities.public_site.public_demo_limits import (
    PUBLIC_DEMO_MESSAGES_PER_CONVERSATION,
)

LOGGER: logging.Logger = logging.getLogger(__name__)


class ListPublicDemosOrchestrator(
    OrchestratorContract[PublicDemoListQuery, PublicDemoList]
):
    """
    GET /v1/public-demos: every demo business of the landing page, each
    described inside its own storage scope (no platform-wide access for a
    public route). A configured business that is gone or has no published
    assistant is left out and logged, so the page offers only demos that
    can answer.
    """

    def __init__(
        self,
        list_demo_businesses: UseCaseContract[
            PublicDemoListQuery, PublicDemoBusinessIds
        ],
        describe_public_demo: UseCaseContract[PublicDemoCardQuery, PublicDemoCard],
        storage_scope: StorageScopeContract,
    ) -> None:
        self._list_demo_businesses: UseCaseContract[
            PublicDemoListQuery, PublicDemoBusinessIds
        ] = list_demo_businesses
        self._describe_public_demo: UseCaseContract[
            PublicDemoCardQuery, PublicDemoCard
        ] = describe_public_demo
        self._storage_scope: StorageScopeContract = storage_scope

    def execute(self, input_data: PublicDemoListQuery) -> PublicDemoList:
        demos: list[PublicDemoCard] = []
        listed = self._list_demo_businesses.run(input_data)
        for business_id in listed.business_ids:
            try:
                with self._storage_scope.scoped_to_business(business_id):
                    demos.append(
                        self._describe_public_demo.run(
                            PublicDemoCardQuery(
                                business_id=business_id,
                                language=input_data.language,
                            )
                        )
                    )
            except NotFoundError:
                LOGGER.warning(
                    "Public demo %s is configured but cannot answer: no such "
                    "business or no published assistant.",
                    business_id,
                )

        return PublicDemoList(
            demos=demos,
            messages_per_hour=PublicDemoMessagesLeft(
                PUBLIC_DEMO_MESSAGES_PER_CONVERSATION
            ),
        )
