import logging

from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
    AssembleAssistantVersionRequest,
)
from app.schemas.dto.assistants.assistant_views import AssistantVersionDetails
from app.schemas.dto.conversation_feed.owner_test_chat import OwnerTestChatCommand
from app.schemas.exceptions.base_exception import ApplicationError
from app.use_cases.shared.test_chat_versions import TESTABLE_STATUSES
from app.utilities.setup.pending_changes import has_unapplied_changes

LOGGER: logging.Logger = logging.getLogger(__name__)


class PrepareTestChatVersionUseCase(UseCaseContract[OwnerTestChatCommand, None]):
    """
    "Try your assistant" before going live and with the latest edits: when
    the version the owner's test chat would talk to (the newest one not
    archived, else the live one) was built before the last change of the
    profile, knowledge, resources or languages, or there is no version
    yet, a fresh DRAFT is built from what the business has now. A draft is
    only a preview: nothing is checked or published, and the next "Apply
    changes" builds its own version.

    Building a version is an owner's action, so for staff, a test of a
    chosen version, or a profile that cannot be built from yet (blocking
    gaps), the test chat goes on with the versions there are.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        assemble_assistant_version: UseCaseContract[
            AssembleAssistantVersionCommand,
            AssistantVersionDetails,
        ],
        assistant_version_repo: AssistantVersionRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._assemble_assistant_version: UseCaseContract[
            AssembleAssistantVersionCommand,
            AssistantVersionDetails,
        ] = assemble_assistant_version
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )

    def run(self, input_data: OwnerTestChatCommand) -> None:
        if input_data.request.assistant_version_id is not None:
            return

        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        is_owner: bool = any(
            member.user_id == input_data.user_id
            and member.role is BusinessMemberRole.OWNER
            for member in business.members
        )
        if not is_owner or self._is_up_to_date(business):
            return

        try:
            self._assemble_assistant_version.run(
                AssembleAssistantVersionCommand(
                    user_id=input_data.user_id,
                    business_id=business.id,
                    request=AssembleAssistantVersionRequest(run_autotests=False),
                )
            )
        except ApplicationError as refusal:
            # Not ready to build from yet: the test chat says so itself.
            LOGGER.info(
                "No preview version for the test chat of business %s: %s",
                business.id,
                refusal,
            )

    def _is_up_to_date(self, business: BusinessDocument) -> bool:
        """Whether the version the test chat would pick has every change."""

        candidates: list[AssistantVersionDocument] = [
            version
            for version in self._assistant_version_repo.list_by_business(business.id)
            if version.status in TESTABLE_STATUSES
        ]
        tested: AssistantVersionDocument | None = max(
            candidates,
            key=lambda version: int(version.version_number),
            default=None,
        )
        if tested is None:
            return False

        return not has_unapplied_changes(
            business,
            tested,
            self._business_profile_repo.get_by_business(business.id),
            self._knowledge_item_repo.list_by_business(business.id),
            self._resource_repo.list_by_business(business.id),
            self._schedule_exception_repo.list_by_business(business.id),
        )
