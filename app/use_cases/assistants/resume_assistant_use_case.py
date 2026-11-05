from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants.assembly_sources import AssistantVersionActivation


class ResumeAssistantUseCase(UseCaseContract[BusinessDocument, None]):
    """
    A paused business goes live again with its published version: the
    version is activated once more, so the launch conditions are checked
    again and the voice agent removed at pause is set up anew. The given
    business may carry the caller's other changes: activation writes it
    whole, and only while nobody saved the business since it was read (a
    stale-revision ConflictError otherwise). A business without a published
    version only changes its status (the caller stores it).
    """

    def __init__(
        self,
        assistant_version_repo: AssistantVersionRepoContract,
        activate_assistant_version: UseCaseContract[
            AssistantVersionActivation,
            AssistantVersionDocument,
        ],
    ) -> None:
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._activate_assistant_version: UseCaseContract[
            AssistantVersionActivation,
            AssistantVersionDocument,
        ] = activate_assistant_version

    def run(self, input_data: BusinessDocument) -> None:
        business: BusinessDocument = input_data
        version: AssistantVersionDocument | None = (
            None
            if business.published_assistant_version_id is None
            else self._assistant_version_repo.get(
                business.id, business.published_assistant_version_id
            )
        )
        if version is None:
            business.status = BusinessStatus.LIVE
            return

        self._activate_assistant_version.run(
            AssistantVersionActivation(
                business=business,
                version=version,
                carries_business_changes=True,
            )
        )
