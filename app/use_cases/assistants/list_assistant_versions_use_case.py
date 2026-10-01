from app.contracts.repositories import AssistantVersionRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants import AssistantVersionsQuery, AssistantVersionSummary


class ListAssistantVersionsUseCase(
    UseCaseContract[AssistantVersionsQuery, list[AssistantVersionSummary]]
):
    """Version history of a business, newest first (owners and staff)."""

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        assistant_version_repo: AssistantVersionRepoContract,
        version_summary_transformer: TransformerContract[
            AssistantVersionDocument,
            AssistantVersionSummary,
        ],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._version_summary_transformer: TransformerContract[
            AssistantVersionDocument,
            AssistantVersionSummary,
        ] = version_summary_transformer

    def run(self, input_data: AssistantVersionsQuery) -> list[AssistantVersionSummary]:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        versions: list[AssistantVersionDocument] = sorted(
            self._assistant_version_repo.list_by_business(business.id),
            key=lambda version: int(version.version_number),
            reverse=True,
        )
        return [
            self._version_summary_transformer.transform(version) for version in versions
        ]
